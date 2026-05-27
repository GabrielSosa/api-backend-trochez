// Routes (all require Bearer token):
//   GET    /api-appraisals?skip=0&limit=50     -> paginated list
//   GET    /api-appraisals/search?q=...        -> search by plate/owner/vin/brand/model
//   GET    /api-appraisals/{id}                -> appraisal + deductions
//   POST   /api-appraisals                     -> create appraisal (+ deductions)
//   PUT    /api-appraisals/{id}                -> update appraisal (+ replace deductions)
//   DELETE /api-appraisals/{id}                -> delete (cascades deductions)

import { errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { isHttpError, requireUser, TokenUser } from "../_shared/auth.ts";

interface DeductionInput {
  deduction_name?: string | null;
  deduction_percentage?: number | null;
  deduction_value?: number | null;
}

interface AppraisalBody {
  user_id?: number | null;
  appraisal_date?: string | null;
  vehicle_brand?: string | null;
  vehicle_model?: string | null;
  vehicle_year?: number | null;
  vehicle_color?: string | null;
  vehicle_plate?: string | null;
  vehicle_mileage?: number | null;
  vehicle_vin?: string | null;
  vehicle_engine?: string | null;
  base_value?: number | null;
  final_value?: number | null;
  notes?: string | null;
  owner_name?: string | null;
  owner_id?: string | null;
  owner_phone?: string | null;
  owner_email?: string | null;
  deductions?: DeductionInput[];
}

const APPRAISAL_COLUMNS = [
  "vehicle_appraisal_id",
  "user_id",
  "appraisal_date",
  "vehicle_brand",
  "vehicle_model",
  "vehicle_year",
  "vehicle_color",
  "vehicle_plate",
  "vehicle_mileage",
  "vehicle_vin",
  "vehicle_engine",
  "base_value",
  "final_value",
  "notes",
  "owner_name",
  "owner_id",
  "owner_phone",
  "owner_email",
].join(",");

function pickAppraisalFields(body: AppraisalBody, currentUserId: number) {
  return {
    user_id: body.user_id ?? currentUserId,
    appraisal_date: body.appraisal_date ?? null,
    vehicle_brand: body.vehicle_brand ?? null,
    vehicle_model: body.vehicle_model ?? null,
    vehicle_year: body.vehicle_year ?? null,
    vehicle_color: body.vehicle_color ?? null,
    vehicle_plate: body.vehicle_plate ?? null,
    vehicle_mileage: body.vehicle_mileage ?? null,
    vehicle_vin: body.vehicle_vin ?? null,
    vehicle_engine: body.vehicle_engine ?? null,
    base_value: body.base_value ?? null,
    final_value: body.final_value ?? null,
    notes: body.notes ?? null,
    owner_name: body.owner_name ?? null,
    owner_id: body.owner_id ?? null,
    owner_phone: body.owner_phone ?? null,
    owner_email: body.owner_email ?? null,
  };
}

function parseSubpath(pathname: string): { id: number | null; tail: string | null } {
  const parts = pathname.split("/").filter(Boolean);
  const idx = parts.findIndex((p) => p === "api-appraisals");
  if (idx === -1 || idx === parts.length - 1) return { id: null, tail: null };
  const next = parts[idx + 1];
  if (next === "search") return { id: null, tail: "search" };
  const n = Number(next);
  if (Number.isInteger(n)) return { id: n, tail: null };
  return { id: null, tail: next };
}

async function loadAppraisalWithDeductions(id: number) {
  const supabase = getSupabase();
  const { data: appraisal, error } = await supabase
    .from("vehicle_appraisal")
    .select(APPRAISAL_COLUMNS)
    .eq("vehicle_appraisal_id", id)
    .maybeSingle();
  if (error || !appraisal) return null;

  const { data: deductions } = await supabase
    .from("appraisal_deductions")
    .select("deduction_id, vehicle_appraisal_id, deduction_name, deduction_percentage, deduction_value")
    .eq("vehicle_appraisal_id", id)
    .order("deduction_id", { ascending: true });

  return { ...appraisal, deductions: deductions ?? [] };
}

async function handleList(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const limit = Math.max(1, Math.min(500, Number(url.searchParams.get("limit") ?? "50") | 0));
  // Accept either ?skip=N or ?page=N (page is 1-indexed) — frontend sends page.
  const pageParam = url.searchParams.get("page");
  const skip = pageParam !== null
    ? Math.max(0, (Math.max(1, Number(pageParam) | 0) - 1) * limit)
    : Math.max(0, Number(url.searchParams.get("skip") ?? "0") | 0);

  const supabase = getSupabase();
  const { data, error, count } = await supabase
    .from("vehicle_appraisal")
    .select(APPRAISAL_COLUMNS, { count: "exact" })
    .order("vehicle_appraisal_id", { ascending: false })
    .range(skip, skip + limit - 1);
  if (error) return errorResponse(error.message, 500);

  const page = Math.floor(skip / limit) + 1;
  const totalPages = limit > 0 ? Math.ceil((count ?? 0) / limit) : 0;
  return jsonResponse({
    items: data ?? [],
    total: count ?? 0,
    skip,
    limit,
    page,
    total_pages: totalPages,
  });
}

async function handleSearch(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") ?? "").trim();
  if (!q) return jsonResponse({ items: [] });

  const supabase = getSupabase();
  const like = `%${q}%`;
  const { data, error } = await supabase
    .from("vehicle_appraisal")
    .select(APPRAISAL_COLUMNS)
    .or(
      [
        `vehicle_plate.ilike.${like}`,
        `owner_name.ilike.${like}`,
        `vehicle_vin.ilike.${like}`,
        `vehicle_brand.ilike.${like}`,
        `vehicle_model.ilike.${like}`,
      ].join(","),
    )
    .order("vehicle_appraisal_id", { ascending: false })
    .limit(100);
  if (error) return errorResponse(error.message, 500);
  return jsonResponse({ items: data ?? [] });
}

async function handleCreate(req: Request, user: TokenUser): Promise<Response> {
  let body: AppraisalBody;
  try {
    body = await req.json();
  } catch (_) {
    return errorResponse("Invalid JSON body", 400);
  }

  const supabase = getSupabase();
  const insertRow = pickAppraisalFields(body, user.user_id);

  const { data: created, error } = await supabase
    .from("vehicle_appraisal")
    .insert(insertRow)
    .select(APPRAISAL_COLUMNS)
    .single();
  if (error || !created) {
    console.error("create appraisal error", error);
    return errorResponse(error?.message ?? "Could not create appraisal", 500);
  }

  const deductions = Array.isArray(body.deductions) ? body.deductions : [];
  if (deductions.length > 0) {
    const rows = deductions.map((d) => ({
      vehicle_appraisal_id: created.vehicle_appraisal_id,
      deduction_name: d.deduction_name ?? null,
      deduction_percentage: d.deduction_percentage ?? null,
      deduction_value: d.deduction_value ?? null,
    }));
    const { error: dErr } = await supabase.from("appraisal_deductions").insert(rows);
    if (dErr) {
      console.error("create deductions error", dErr);
      return errorResponse(dErr.message, 500);
    }
  }

  const result = await loadAppraisalWithDeductions(created.vehicle_appraisal_id);
  return jsonResponse(result, 201);
}

async function handleUpdate(req: Request, id: number, user: TokenUser): Promise<Response> {
  let body: AppraisalBody;
  try {
    body = await req.json();
  } catch (_) {
    return errorResponse("Invalid JSON body", 400);
  }

  const supabase = getSupabase();
  const update = pickAppraisalFields(body, user.user_id);

  const { data: updated, error } = await supabase
    .from("vehicle_appraisal")
    .update(update)
    .eq("vehicle_appraisal_id", id)
    .select(APPRAISAL_COLUMNS)
    .maybeSingle();
  if (error) return errorResponse(error.message, 500);
  if (!updated) return errorResponse("Appraisal not found", 404);

  if (Array.isArray(body.deductions)) {
    await supabase.from("appraisal_deductions").delete().eq("vehicle_appraisal_id", id);
    if (body.deductions.length > 0) {
      const rows = body.deductions.map((d) => ({
        vehicle_appraisal_id: id,
        deduction_name: d.deduction_name ?? null,
        deduction_percentage: d.deduction_percentage ?? null,
        deduction_value: d.deduction_value ?? null,
      }));
      const { error: dErr } = await supabase.from("appraisal_deductions").insert(rows);
      if (dErr) return errorResponse(dErr.message, 500);
    }
  }

  const result = await loadAppraisalWithDeductions(id);
  return jsonResponse(result);
}

async function handleDelete(id: number): Promise<Response> {
  const supabase = getSupabase();
  // Manual cascade: appraisal_deductions does not have ON DELETE CASCADE in the DDL.
  await supabase.from("appraisal_deductions").delete().eq("vehicle_appraisal_id", id);
  const { error } = await supabase
    .from("vehicle_appraisal")
    .delete()
    .eq("vehicle_appraisal_id", id);
  if (error) return errorResponse(error.message, 500);
  return jsonResponse({ detail: "Appraisal deleted" });
}

Deno.serve(withErrorBoundary(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  let user: TokenUser;
  try {
    user = await requireUser(req);
  } catch (e) {
    if (isHttpError(e)) return errorResponse(e.message, e.status);
    throw e;
  }

  const url = new URL(req.url);
  const { id, tail } = parseSubpath(url.pathname);

  if (req.method === "GET" && tail === "search") return handleSearch(req);

  if (req.method === "GET" && id === null && tail === null) return handleList(req);

  if (req.method === "GET" && id !== null) {
    const result = await loadAppraisalWithDeductions(id);
    if (!result) return errorResponse("Appraisal not found", 404);
    return jsonResponse(result);
  }

  if (req.method === "POST" && id === null && tail === null) {
    return handleCreate(req, user);
  }

  if (req.method === "PUT" && id !== null) return handleUpdate(req, id, user);
  if (req.method === "DELETE" && id !== null) return handleDelete(id);

  return errorResponse("Not found", 404);
}));
