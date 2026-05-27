// Routes (all require Bearer token):
// GET /api-dashboard/summary           -> totals & comparisons month vs. previous
// GET /api-dashboard/ventas-dia        -> today's appraisals
// GET /api-dashboard/ventas-mes        -> current-month appraisals grouped by day
// GET /api-dashboard/carros-mas-avaluos -> top vehicles by appraisal count

import { errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { isHttpError, requireUser } from "../_shared/auth.ts";

function getSubroute(pathname: string): string | null {
  const parts = pathname.split("/").filter(Boolean);
  const idx = parts.findIndex((p) => p === "api-dashboard");
  if (idx === -1 || idx === parts.length - 1) return null;
  return parts[idx + 1];
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthRange(offsetMonths = 0): { start: string; end: string } {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + offsetMonths, 1));
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + offsetMonths + 1, 1));
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

async function handleSummary(): Promise<Response> {
  const supabase = getSupabase();
  const current = monthRange(0);
  const previous = monthRange(-1);

  // Use appraisal_value_trochez as the primary value (local currency)
  const [{ data: curRows, error: curErr }, { data: prevRows, error: prevErr }] = await Promise.all([
    supabase
      .from("vehicle_appraisal")
      .select("vehicle_appraisal_id, appraisal_value_trochez, apprasail_value_lower_cost")
      .gte("appraisal_date", current.start)
      .lt("appraisal_date", current.end),
    supabase
      .from("vehicle_appraisal")
      .select("vehicle_appraisal_id, appraisal_value_trochez, apprasail_value_lower_cost")
      .gte("appraisal_date", previous.start)
      .lt("appraisal_date", previous.end),
  ]);
  if (curErr) return errorResponse(curErr.message, 500);
  if (prevErr) return errorResponse(prevErr.message, 500);

  const sum = (
    rows: Array<{ appraisal_value_trochez: number | null; apprasail_value_lower_cost: number | null }> | null,
    key: "appraisal_value_trochez" | "apprasail_value_lower_cost",
  ) => (rows ?? []).reduce((acc, r) => acc + Number(r[key] ?? 0), 0);

  const currentCount = curRows?.length ?? 0;
  const previousCount = prevRows?.length ?? 0;
  const currentFinal = sum(curRows, "appraisal_value_trochez");
  const previousFinal = sum(prevRows, "appraisal_value_trochez");
  const currentBase = sum(curRows, "apprasail_value_lower_cost");
  const previousBase = sum(prevRows, "apprasail_value_lower_cost");

  const pct = (a: number, b: number) =>
    b === 0 ? (a === 0 ? 0 : 100) : Number((((a - b) / b) * 100).toFixed(2));

  return jsonResponse({
    current_month: {
      start: current.start,
      end: current.end,
      count: currentCount,
      total_final_value: currentFinal,
      total_base_value: currentBase,
    },
    previous_month: {
      start: previous.start,
      end: previous.end,
      count: previousCount,
      total_final_value: previousFinal,
      total_base_value: previousBase,
    },
    deltas: {
      count_pct: pct(currentCount, previousCount),
      final_value_pct: pct(currentFinal, previousFinal),
      base_value_pct: pct(currentBase, previousBase),
    },
  });
}

async function handleVentasDia(): Promise<Response> {
  const supabase = getSupabase();
  const today = todayISO();
  const { data, error } = await supabase
    .from("vehicle_appraisal")
    .select(
      "vehicle_appraisal_id, appraisal_date, brand, vehicle_description, plate_number, owner, appraisal_value_trochez, apprasail_value_lower_cost",
    )
    .eq("appraisal_date", today)
    .order("vehicle_appraisal_id", { ascending: false });
  if (error) return errorResponse(error.message, 500);
  return jsonResponse({ date: today, items: data ?? [], total: (data ?? []).length });
}

async function handleVentasMes(): Promise<Response> {
  const supabase = getSupabase();
  const { start, end } = monthRange(0);
  const { data, error } = await supabase
    .from("vehicle_appraisal")
    .select("appraisal_date, appraisal_value_trochez, apprasail_value_lower_cost")
    .gte("appraisal_date", start)
    .lt("appraisal_date", end);
  if (error) return errorResponse(error.message, 500);

  const byDay = new Map<string, { count: number; total_final_value: number; total_base_value: number }>();
  for (const row of data ?? []) {
    const day = (row.appraisal_date as string).slice(0, 10);
    const cur = byDay.get(day) ?? { count: 0, total_final_value: 0, total_base_value: 0 };
    cur.count += 1;
    cur.total_final_value += Number(row.appraisal_value_trochez ?? 0);
    cur.total_base_value += Number(row.apprasail_value_lower_cost ?? 0);
    byDay.set(day, cur);
  }

  const items = [...byDay.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([day, v]) => ({ day, ...v }));

  return jsonResponse({ start, end, items });
}

async function handleCarrosMasAvaluos(): Promise<Response> {
  const supabase = getSupabase();
  // Group by brand + vehicle_description for meaningful grouping
  const { data, error } = await supabase
    .from("vehicle_appraisal")
    .select("brand, vehicle_description");
  if (error) return errorResponse(error.message, 500);

  const counts = new Map<string, { brand: string; vehicle_description: string; count: number }>();
  for (const row of data ?? []) {
    const key = `${row.brand ?? "Unknown"}|${row.vehicle_description ?? ""}`;
    const cur = counts.get(key) ?? { brand: row.brand ?? "Unknown", vehicle_description: row.vehicle_description ?? "", count: 0 };
    cur.count += 1;
    counts.set(key, cur);
  }

  const items = [...counts.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  return jsonResponse({ items });
}

Deno.serve(withErrorBoundary(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  let _user;
  try {
    _user = await requireUser(req);
  } catch (e) {
    if (isHttpError(e)) return errorResponse(e.message, e.status);
    throw e;
  }

  const subroute = getSubroute(new URL(req.url).pathname);

  if (req.method === "GET") {
    if (subroute === "summary") return handleSummary();
    if (subroute === "ventas-dia") return handleVentasDia();
    if (subroute === "ventas-mes") return handleVentasMes();
    if (subroute === "carros-mas-avaluos") return handleCarrosMasAvaluos();
    // Root ping (used by cron job to keep DB alive)
    if (subroute === null) return jsonResponse({ status: "ok" });
  }

  return errorResponse("Not found", 404);
}));
