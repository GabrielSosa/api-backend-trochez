// Routes (all require Bearer token):
// GET  /api-appraisals?skip=0&limit=50     -> paginated list
// GET  /api-appraisals/search?q=...        -> search by plate/owner/vin/brand
// GET  /api-appraisals/{id}                -> appraisal + deductions
// POST /api-appraisals                     -> create appraisal (+ deductions)
// PUT  /api-appraisals/{id}                -> update appraisal (+ replace deductions)
// DELETE /api-appraisals/{id}              -> delete (cascades deductions)

import { errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { isHttpError, requireUser, TokenUser } from "../_shared/auth.ts";

interface DeductionInput {
  deduction_name?: string | null;
  deduction_percentage?: number | null;
  deduction_value?: number | null;
}

// Matches the actual vehicle_appraisal table schema
interface AppraisalBody {
  appraisal_date?: string | null;
  vehicle_description?: string | null;
  brand?: string | null;
  model_year?: number | null;
  color?: string | null;
  mileage?: number | null;
  fuel_type?: string | null;
  engine_size?: string | null;
  plate_number?: string | null;
  applicant?: string | null;
  owner?: string | null;
  appraisal_value_usd?: number | null;
  appraisal_value_trochez?: number | null;
  vin?: string | null;
  engine_number?: string | null;
  notes?: string | null;
  validity_days?: number | null;
  validity_kms?: number | null;
  apprasail_value_lower_cost?: number | null;
  apprasail_value_bank?: number | null;
  apprasail_value_lower_bank?: number | null;
  extras?: string | null;
  vin_card?: string | null;
  engine_number_card?: string | null;
  total_deductions?: number | null;
  modified_km?: number | null;
  extra_value?: number | null;
  discounts?: number | null;
  bank_value_in_dollars?: number | null;
  referencia_original?: number | null;
  cert?: number | null;
  deductions?: DeductionInput[];
}

const APPRAISAL_COLUMNS = [
  "vehicle_appraisal_id",
  "appraisal_date",
  "vehicle_description",
  "brand",
  "model_year",
  "color",
  "mileage",
  "fuel_type",
  "engine_size",
  "plate_number",
  "applicant",
  "owner",
  "appraisal_value_usd",
  "appraisal_value_trochez",
  "vin",
  "engine_number",
  "notes",
  "validity_days",
  "validity_kms",
  "apprasail_value_lower_cost",
  "apprasail_value_bank",
  "apprasail_value_lower_bank",
  "extras",
  "vin_card",
  "engine_number_card",
  "total_deductions",
  "modified_km",
  "extra_value",
  "discounts",
  "bank_value_in_dollars",
  "referencia_original",
  "cert",
].join(",");

function pickAppraisalFields(body: AppraisalBody) {
  return {
    appraisal_date: body.appraisal_date ?? null,
    vehicle_description: body.vehicle_description ?? null,
    brand: body.brand ?? null,
    model_year: body.model_year ?? null,
    color: body.color ?? null,
    mileage: body.mileage ?? null,
    fuel_type: body.fuel_type ?? null,
    engine_size: body.engine_size ?? null,
    plate_number: body.plate_number ?? null,
    applicant: body.applicant ?? null,
    owner: body.owner ?? null,
    appraisal_value_usd: body.appraisal_value_usd ?? null,
    appraisal_value_trochez: body.appraisal_value_trochez ?? null,
    vin: body.vin ?? null,
    engine_number: body.engine_number ?? null,
    notes: body.notes ?? null,
    validity_days: body.validity_days ?? null,
    validity_kms: body.validity_kms ?? null,
    apprasail_value_lower_cost: body.apprasail_value_lower_cost ?? null,
    apprasail_value_bank: body.apprasail_value_bank ?? null,
    apprasail_value_lower_bank: body.apprasail_value_lower_bank ?? null,
    extras: body.extras ?? null,
    vin_card: body.vin_card ?? null,
    engine_number_card: body.engine_number_card ?? null,
    total_deductions: body.total_deductions ?? null,
    modified_km: body.modified_km ?? null,
    extra_value: body.extra_value ?? null,
    discounts: body.discounts ?? null,
    bank_value_in_dollars: body.bank_value_in_dollars ?? null,
    referencia_original: body.referencia_original ?? null,
    cert: body.cert ?? null,
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
  // Accept either ?skip=N or ?page=N (page is 1-indexed)
  const pageParam = url.searchParams.get("page");
  const skip = pageParam !== null
    ? Math.max(0, (Math.max(1, Number(pageParam) | 0) - 1) * limit)
    : Math.max(0, Number(url.searchParams.get("skip") ?? "0") | 0);

  const supabase = getSupabase();
  const { data, error, count } = await supabase
    .from("vehicle_appraisal")
    .select(APPRAISAL_COLUMNS + ",count()", { count: "exact" })
    .order("vehicle_appraisal_id", { ascending: false })
    .range(skip, skip + limit - 1);

  if (error) return errorResponse(error.message, 500);
  return jsonResponse({ items: data ?? [], total: count ?? 0, skip, limit });
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
        `plate_number.ilike.${like}`,
        `owner.ilike.${like}`,
        `vin.ilike.${like}`,
        `brand.ilike.${like}`,
        `vehicle_description.ilike.${like}`,
        `applicant.ilike.${like}`,
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
  const fields = pickAppraisalFields(body);
  const { data: appraisal, error } = await supabase
    .from("vehicle_appraisal")
    .insert(fields)
    .select(APPRAISAL_COLUMNS)
    .single();
  if (error) return errorResponse(error.message, 500);

  const deductions = body.deductions ?? [];
  if (deductions.length > 0) {
    const rows = deductions.map((d) => ({
      vehicle_appraisal_id: appraisal.vehicle_appraisal_id,
      deduction_name: d.deduction_name ?? null,
      deduction_percentage: d.deduction_percentage ?? null,
      deduction_value: d.deduction_value ?? null,
    }));
    const { error: dErr } = await supabase.from("appraisal_deductions").insert(rows);
    if (dErr) return errorResponse(dErr.message, 500);
  }

  const result = await loadAppraisalWithDeductions(appraisal.vehicle_appraisal_id);
  return jsonResponse(result, 201);
}

async function handleUpdate(req: Request, id: number, _user: TokenUser): Promise<Response> {
  let body: AppraisalBody;
  try {
    body = await req.json();
  } catch (_) {
    return errorResponse("Invalid JSON body", 400);
  }

  const supabase = getSupabase();
  const fields = pickAppraisalFields(body);
  const { error } = await supabase
    .from("vehicle_appraisal")
    .update(fields)
    .eq("vehicle_appraisal_id", id);
  if (error) return errorResponse(error.message, 500);

  if (body.deductions !== undefined) {
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
  if (!result) return errorResponse("Appraisal not found", 404);
  return jsonResponse(result);
}

async function handleDelete(id: number): Promise<Response> {
  const supabase = getSupabase();
  const { error } = await supabase
    .from("vehicle_appraisal")
    .delete()
    .eq("vehicle_appraisal_id", id);
  if (error) return errorResponse(error.message, 500);
  return jsonResponse({ deleted: true });
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
