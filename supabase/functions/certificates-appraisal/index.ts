// GET /functions/v1/certificates-appraisal/{id}
//
// Returns an HTML certificate for the appraisal.
//
// Query params:
//   format=html (default) — returns text/html
//   format=json           — returns the raw appraisal + deductions JSON
//
// Auth: required (Bearer token).

import { corsHeaders, errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { isHttpError, requireUser } from "../_shared/auth.ts";

interface AppraisalRow {
  vehicle_appraisal_id: number;
  appraisal_date: string | null;
  brand: string | null;
  vehicle_description: string | null;
  model_year: number | null;
  color: string | null;
  plate_number: string | null;
  mileage: number | null;
  vin: string | null;
  engine_number: string | null;
  apprasail_value_lower_cost: number | null;
  appraisal_value_trochez: number | null;
  appraisal_value_usd: number | null;
  notes: string | null;
  owner: string | null;
  applicant: string | null;
  fuel_type: string | null;
  engine_size: string | null;
  validity_days: number | null;
  validity_kms: number | null;
  extras: string | null;
  cert: string | null;
  referencia_original: string | null;
}

interface DeductionRow {
  deduction_id: number;
  deduction_name: string | null;
  deduction_percentage: number | null;
  deduction_value: number | null;
}

function extractId(pathname: string): number | null {
  const parts = pathname.split("/").filter(Boolean);
  const idx = parts.findIndex((p) => p === "certificates-appraisal");
  if (idx === -1 || idx === parts.length - 1) return null;
  const tail = parts[idx + 1];
  if (tail === "appraisal" && parts.length > idx + 2) {
    const n = Number(parts[idx + 2]);
    return Number.isInteger(n) ? n : null;
  }
  const n = Number(tail);
  return Number.isInteger(n) ? n : null;
}

function esc(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtMoney(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "";
  const n = Number(v);
  if (Number.isNaN(n)) return "";
  return n.toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderHtml(a: AppraisalRow, deductions: DeductionRow[]): string {
  const rows = deductions
    .map(
      (d) => `
        <tr>
          <td>${esc(d.deduction_name)}</td>
          <td class="num">${d.deduction_percentage ?? ""}</td>
          <td class="num">${fmtMoney(d.deduction_value)}</td>
        </tr>`,
    )
    .join("");

  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>Certificado de avaluo #${a.vehicle_appraisal_id}</title>
<style>
  body { font-family: Arial, Helvetica, sans-serif; margin: 40px; color: #222; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { font-size: 14px; margin-top: 28px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
  .meta { color: #666; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
  th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
  th { background: #f5f5f5; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; font-size: 13px; }
  .grid .k { color: #666; }
  .totals { margin-top: 14px; font-size: 14px; }
  .totals .row { display: flex; justify-content: space-between; padding: 4px 0; }
  .totals .final { font-weight: bold; border-top: 1px solid #888; padding-top: 8px; margin-top: 8px; }
  @media print { body { margin: 20px; } }
</style>
</head>
<body>
  <h1>Certificado de Avaluo Vehicular</h1>
  <div class="meta">Folio #${a.vehicle_appraisal_id} · Fecha: ${esc(a.appraisal_date ?? "")} · Ref: ${esc(a.cert ?? "")}</div>

  <h2>Datos del vehiculo</h2>
  <div class="grid">
    <div class="k">Marca</div><div>${esc(a.brand)}</div>
    <div class="k">Modelo</div><div>${esc(a.vehicle_description)}</div>
    <div class="k">Anio</div><div>${esc(a.model_year)}</div>
    <div class="k">Color</div><div>${esc(a.color)}</div>
    <div class="k">Placa</div><div>${esc(a.plate_number)}</div>
    <div class="k">Kilometraje</div><div>${esc(a.mileage)}</div>
    <div class="k">Combustible</div><div>${esc(a.fuel_type)}</div>
    <div class="k">Motor</div><div>${esc(a.engine_size)}</div>
    <div class="k">VIN</div><div>${esc(a.vin)}</div>
    <div class="k">No. Motor</div><div>${esc(a.engine_number)}</div>
  </div>

  <h2>Propietario / Solicitante</h2>
  <div class="grid">
    <div class="k">Propietario</div><div>${esc(a.owner)}</div>
    <div class="k">Solicitante</div><div>${esc(a.applicant)}</div>
  </div>

  <h2>Deducciones</h2>
  <table>
    <thead>
      <tr><th>Concepto</th><th class="num">%</th><th class="num">Valor</th></tr>
    </thead>
    <tbody>${rows || `<tr><td colspan="3" style="text-align:center;color:#888">Sin deducciones</td></tr>`}</tbody>
  </table>

  <div class="totals">
    <div class="row"><span>Valor base</span><span class="num">${fmtMoney(a.apprasail_value_lower_cost)}</span></div>
    <div class="row"><span>Valor banco</span><span class="num">${fmtMoney(a.appraisal_value_usd)}</span></div>
    <div class="row final"><span>Valor final (Lempiras)</span><span class="num">${fmtMoney(a.appraisal_value_trochez)}</span></div>
  </div>

  ${a.validity_days ? `<div class="meta" style="margin-top:12px">Validez: ${a.validity_days} dias / ${a.validity_kms ?? "N/A"} kms</div>` : ""}
  ${a.notes ? `<h2>Notas</h2><div>${esc(a.notes)}</div>` : ""}
  ${a.extras ? `<h2>Extras</h2><div>${esc(a.extras)}</div>` : ""}
</body>
</html>`;
}

Deno.serve(withErrorBoundary(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  try {
    await requireUser(req);
  } catch (e) {
    if (isHttpError(e)) return errorResponse(e.message, e.status);
    throw e;
  }

  if (req.method !== "GET") return errorResponse("Method not allowed", 405);

  const url = new URL(req.url);
  const id = extractId(url.pathname);
  if (id === null) return errorResponse("Appraisal id is required", 400);

  const supabase = getSupabase();
  const { data: appraisal, error } = await supabase
    .from("vehicle_appraisal")
    .select("*")
    .eq("vehicle_appraisal_id", id)
    .maybeSingle();
  if (error) return errorResponse(error.message, 500);
  if (!appraisal) return errorResponse("Appraisal not found", 404);

  const { data: deductions } = await supabase
    .from("appraisal_deductions")
    .select("deduction_id, deduction_name, deduction_percentage, deduction_value")
    .eq("vehicle_appraisal_id", id)
    .order("deduction_id", { ascending: true });

  const format = (url.searchParams.get("format") ?? "html").toLowerCase();
  if (format === "json") {
    return jsonResponse({ ...appraisal, deductions: deductions ?? [] });
  }

  const html = renderHtml(appraisal as AppraisalRow, (deductions ?? []) as DeductionRow[]);
  return new Response(html, {
    status: 200,
    headers: { ...corsHeaders, "Content-Type": "text/html; charset=utf-8" },
  });
}));
