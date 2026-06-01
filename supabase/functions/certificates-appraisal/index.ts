// GET /functions/v1/certificates-appraisal/{id}
// GET /functions/v1/certificates-appraisal/appraisal/{id}
//
// Port fiel del template del backend FastAPI original
// (app/certs/certificado.html). El navegador renderiza el HTML y permite
// imprimir a PDF (Ctrl+P / Cmd+P).
//
// Schema:
//  - vehicle_appraisal: nombres originales (brand, vehicle_description,
//    model_year, owner, applicant, vin, engine_number, validity_days,
//    validity_kms, appraisal_value_usd, apprasail_value_lower_cost, extras).
//  - appraisal_deductions: usa los nombres nuevos (deduction_name,
//    deduction_percentage, deduction_value).
//
// Query params:
//   format=html (default) — text/html
//   format=json           — appraisal + deductions raw JSON
//
// Auth: Bearer token requerido.

import { corsHeaders, errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { isHttpError, requireUser } from "../_shared/auth.ts";
import { LOGO_DATA_URL } from "./_assets.ts";

interface AppraisalRow {
  vehicle_appraisal_id: number;
  appraisal_date: string | null;
  brand: string | null;
  vehicle_description: string | null;
  model_year: number | null;
  color: string | null;
  plate_number: string | null;
  mileage: number | null;
  fuel_type: string | null;
  engine_size: number | string | null;
  origin: string | null;
  vin: string | null;
  engine_number: string | null;
  applicant: string | null;
  owner: string | null;
  notes: string | null;
  validity_days: number | null;
  validity_kms: number | null;
  extras: string | null;
  vin_card: string | null;
  engine_number_card: string | null;
  appraisal_value_usd: number | string | null;
  appraisal_value_trochez: number | string | null;
  apprasail_value_lower_cost: number | string | null;
  apprasail_value_bank: number | string | null;
  apprasail_value_lower_bank: number | string | null;
  bank_value_in_dollars: number | string | null;
  cert: number | string | null;
  referencia_original: number | string | null;
}

interface DeductionRow {
  appraisal_deductions_id: number;
  description: string | null;
  amount: number | string | null;
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

function toNumber(v: number | string | null | undefined): number {
  if (v === null || v === undefined || v === "") return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

// Replica `f"{value:,}".replace(",", " ")` del backend original.
function fmtIntSpaced(n: number): string {
  return Math.trunc(n).toLocaleString("en-US").replaceAll(",", " ");
}

// Equivalente a CertificateService.number_to_words (Spanish, hasta millones).
function numberToWords(n: number): string {
  const units = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"];
  const teens = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"];
  const tens = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"];

  if (n === 0) return "CERO";
  if (n < 10) return units[n];
  if (n < 20) return teens[n - 10];
  if (n < 100) {
    return tens[Math.floor(n / 10)] + (n % 10 !== 0 ? " Y " + units[n % 10] : "");
  }
  if (n < 1000) {
    const hundreds =
      n === 100 ? "CIEN" :
      n < 200 ? "CIENTO" :
      n < 300 ? "DOSCIENTOS" :
      n < 400 ? "TRESCIENTOS" :
      n < 500 ? "CUATROCIENTOS" :
      n < 600 ? "QUINIENTOS" :
      n < 700 ? "SEISCIENTOS" :
      n < 800 ? "SETECIENTOS" :
      n < 900 ? "OCHOCIENTOS" : "NOVECIENTOS";
    return hundreds + (n % 100 !== 0 ? " " + numberToWords(n % 100) : "");
  }
  if (n < 1_000_000) {
    const head = n < 2000 ? "UN MIL" : numberToWords(Math.floor(n / 1000)) + " MIL";
    return head + (n % 1000 !== 0 ? " " + numberToWords(n % 1000) : "");
  }
  const head = n < 2_000_000 ? "UN MILLÓN" : numberToWords(Math.floor(n / 1_000_000)) + " MILLONES";
  return head + (n % 1_000_000 !== 0 ? " " + numberToWords(n % 1_000_000) : "");
}

const MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
function formatDate(input: string | null): string {
  let d: Date;
  if (input) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(input);
    if (m) {
      d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    } else {
      d = new Date(input);
      if (isNaN(d.getTime())) d = new Date();
    }
  } else {
    d = new Date();
  }
  const day = String(d.getDate()).padStart(2, "0");
  const mon = MONTHS_ES[d.getMonth()];
  return `${day} ${mon} ${d.getFullYear()}`;
}

function renderHtml(a: AppraisalRow, deductions: DeductionRow[]): string {
  const formattedDate = formatDate(a.appraisal_date);

  // Número de certificado real (columna `cert`, numeric → llega como 22374.0).
  // Si no hay certificado cargado, el recuadro queda en blanco (no se cae al
  // id interno autoincremental).
  const certNum = toNumber(a.cert);
  const formattedCert = certNum > 0 ? String(Math.trunc(certNum)) : "";

  const totalDeductions = deductions.reduce((sum, d) => sum + toNumber(d.amount), 0);
  const formattedTotalDeductions = `₡${fmtIntSpaced(totalDeductions)}`;

  // Lado derecho: "VALOR SUGERIDO PARA ENTREGA EN DISTRIBUIDORA" -> appraisal_value_usd
  const appraisalUsd = toNumber(a.appraisal_value_usd);
  const formattedAppraisalValue = appraisalUsd > 0 ? `$${fmtIntSpaced(appraisalUsd)}` : "";
  const appraisalValueWords = appraisalUsd > 0 ? numberToWords(Math.trunc(appraisalUsd)) : "";

  // Lado izquierdo: "VALOR MAXIMO DE GARANTIA BANCARIA" -> bank_value_in_dollars (USD).
  // Si el avalúo no tiene ese input cargado, el bloque queda vacío en lugar de
  // mostrar el valor del avalúo en CRC con el cartel "DÓLARES" (que es lo que
  // estaba pasando con apprasail_value_lower_cost).
  const bankUsd = toNumber(a.bank_value_in_dollars);
  const formattedBankValue = bankUsd > 0 ? `$${fmtIntSpaced(bankUsd)}` : "";
  const bankValueWords = bankUsd > 0 ? numberToWords(Math.trunc(bankUsd)) : "";

  const deductionRows = deductions
    .map(
      (d) => `
            <tr>
                <td>${esc(d.description)}</td>
                <td>${esc(d.amount ?? "")}</td>
            </tr>`,
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Certificado de Avalúo - Trochez</title>
    <style>
        @page {
            size: letter;
            margin: 0;
        }
        /* Force backgrounds (the pastel-blue bands) to render on paper / PDF.
           Without this Chrome/Safari/Edge strip every background-color and
           the printed certificate comes out all-white. */
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: white;
        }
        .page-container {
            width: 21.59cm;
            height: 27.94cm;
            padding: 1cm;
            margin: 0 auto;
            background: white;
            position: relative;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }
        .header-logo {
            position: absolute;
            top: 1cm;
            left: 1cm;
            padding: 0;
            max-width: 200px;
        }
        .watermark {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            opacity: 0.15;
            z-index: 0;
            pointer-events: none;
        }
        .watermark img {
            max-width: 450px;
        }
        .header-info {
            position: absolute;
            top: 1cm;
            right: 1cm;
            text-align: right;
            font-size: 14px;
            border: 1px solid #000;
            padding: 10px 15px;
        }
        .main-title {
            text-align: center;
            font-size: 26px;
            font-weight: bold;
            margin-top: 2cm;
            margin-bottom: 0.5cm;
        }
        .info-section {
            background: #dbe7f3;
            padding: 10px;
            margin-bottom: 8px;
        }
        .vehicle-info {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            table-layout: fixed;
        }
        .vehicle-info td {
            padding: 5px;
        }
        .label-cell {
            font-weight: bold;
            width: 100px;
            background-color: #dbe7f3;
        }
        .small-label {
            font-size: 10px;
            color: #666;
            display: block;
        }
        .diagnosis-header {
            background-color: #dbe7f3;
            padding: 4px 8px;
            font-weight: bold;
            font-size: 12px;
        }
        .diagnosis-content {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
            font-size: 12px;
        }
        .diagnosis-content td {
            padding: 4px 8px;
            border-bottom: 1px dotted #ccc;
            line-height: 1.3;
        }
        .diagnosis-content td:last-child {
            text-align: right;
            width: 120px;
            font-variant-numeric: tabular-nums;
        }
        .total-amount {
            text-align: left;
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0;
        }
        .amount-text {
            text-align: left;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .values-section {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            margin-top: 10px;
            width: 100%;
        }
        .value-box {
            border: 2px solid #000;
            padding: 5px;
            width: 300px;
            text-align: center;
            font-size: 11px;
            white-space: nowrap;
        }
        .expenses-row {
            width: 100%;
            display: flex;
            justify-content: flex-end;
            margin-top: 15px;
        }
        .notes-section {
            text-align: left;
            font-size: 12px;
            margin: 8px 0;
        }
        /* Pie de página: fluye al final del contenedor y se ancla al fondo con
           margin-top:auto, en lugar de posicionarse en absolute (que se solapaba
           con el contenido cuando la tabla de Diagnóstico crece). */
        .page-footer {
            margin-top: auto;
        }
        .footer-note {
            font-size: 10px;
            margin: 8px 0;
            text-align: justify;
        }
        .vin-section {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            border-top: 1px solid #000;
            padding-top: 10px;
            background: white;
        }
        .vin-label {
            font-weight: bold;
            font-size: 12px;
        }
        .validity-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 12px;
        }
        .validity-stamp {
            border: 2px solid red;
            color: red;
            padding: 6px 14px;
            font-weight: bold;
            white-space: nowrap;
            z-index: 2;
            text-align: center;
            font-size: 12px;
            line-height: 1.1;
            background: white;
        }
    </style>
</head>
<body>
    <div class="page-container">
        <div class="header-logo">
            <img src="${LOGO_DATA_URL}" alt="Logo Avalúo Trochez" style="max-height: 180px; max-width: 100%;">
        </div>
        <div class="watermark">
            <img src="${LOGO_DATA_URL}" alt="Watermark">
        </div>
        <div class="header-info">
            <div style="text-align: center;">${esc(formattedDate)}</div>
            SAN JOSE C.R<br>
            Tel. 8794-4104<br>
            <div style="text-align: center; margin-top: 5px;">${esc(formattedCert)}</div>
        </div>
        <div class="main-title">Certificado de Avalúo</div>

        <div class="info-section" style="padding: 0; background: #dbe7f3; border-top: 2px solid #dbe7f3;">
            <table class="vehicle-info" style="margin-bottom: 0;">
                <tr>
                    <td class="label-cell" style="width: 100px; border-bottom: 2px solid white;">Vehículo</td>
                    <td style="background-color: white; padding: 5px 10px; width: 30%; line-height: 1.3;">
                        <div>${esc(a.brand)}</div>
                        <div style="margin-top: 2px;">${esc(a.vehicle_description)}</div>
                    </td>
                    <td style="padding: 5px 10px; background-color: #dbe7f3;" colspan="5">
                        <table style="width: 100%;">
                            <tr>
                                <td style="text-align: center;"><span class="small-label">AÑO</span>${esc(a.model_year)}</td>
                                <td style="text-align: center;"><span class="small-label">ORIGEN</span>${a.origin ? esc(a.origin) : "MEX/AGE"}</td>
                                <td style="text-align: center;"><span class="small-label">KM</span>${esc(a.mileage)}</td>
                                <td style="text-align: center;"><span class="small-label">COMB</span>${esc(a.fuel_type)}</td>
                                <td style="text-align: center;"><span class="small-label">CILINDRADA</span>${esc(a.engine_size)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td class="label-cell" style="width: 100px; border-bottom: 2px solid white;">Solicitante</td>
                    <td style="background-color: white; padding: 5px 10px;" colspan="1">${esc(a.applicant)}</td>
                    <td style="padding: 5px 10px; background-color: #dbe7f3;" colspan="5">
                        <table style="width: 100%;">
                            <tr>
                                <td style="text-align: left;"><span class="small-label">COLOR</span>${esc(a.color)}</td>
                                <td colspan="3"></td>
                                <td style="text-align: right;"><span class="small-label">PLACAS</span>${esc(a.plate_number)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td class="label-cell" style="width: 100px; border-bottom: 2px solid white;">Propietario</td>
                    <td style="background-color: white; padding: 5px 10px;" colspan="1">${esc(a.owner)}</td>
                    <td style="padding: 5px 10px; background-color: #dbe7f3;" colspan="5">
                        <table style="width: 100%;">
                            <tr>
                                <td colspan="6">${esc(a.extras)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </div>

        <div class="diagnosis-header">Diagnostico</div>
        <table class="diagnosis-content">${deductionRows}
        </table>

        <div class="notes-section">
            <div style="font-weight: bold;">NOTA: ${esc(a.notes)}</div>
        </div>

        <div class="values-section" style="margin-bottom: 10px;">
            <table style="width: 100%; border-collapse: separate; border-spacing: 40px 0;">
                <tr>
                    <td style="text-align: center; vertical-align: middle; height: 60px;">
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                            ${formattedBankValue ? `
                                <div class="total-amount">${esc(formattedBankValue)}</div>
                                <div class="amount-text">${esc(bankValueWords)} DÓLARES</div>
                            ` : ""}
                        </div>
                    </td>
                    <td style="text-align: center; vertical-align: middle; height: 60px;">
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                            ${formattedAppraisalValue ? `
                                <div class="total-amount">${esc(formattedAppraisalValue)}</div>
                                <div class="amount-text">${esc(appraisalValueWords)} DÓLARES</div>
                            ` : ""}
                        </div>
                    </td>
                </tr>
                <tr>
                    <td style="text-align: center;">
                        <div class="value-box">VALOR MAXIMO DE GARANTIA BANCARIA</div>
                    </td>
                    <td style="text-align: center;">
                        <div class="value-box">VALOR SUGERIDO PARA ENTREGA EN DISTRIBUIDORA</div>
                    </td>
                </tr>
            </table>
        </div>

        <div class="expenses-row">
            <table style="width: auto; margin-left: auto;">
                <tr>
                    <td style="text-align: right; padding-right: 20px;"><strong>TOTAL DE GASTOS</strong></td>
                    <td><strong>${esc(formattedTotalDeductions)}</strong></td>
                </tr>
            </table>
        </div>

        <div class="page-footer">
        <div class="footer-note">
            Nota: Los gastos de reparación y la depreciación por kilometraje están rebajados. Condiciones de Servicio: En lo sucesivo "la empresa" se refiere a Avalúos Trochez. El valor emitido en este documento se ha determinado en base a la experiencia de ventas pasada de autolotes y personas particulares y no podemos anticipar todos los factores presentes o futuros que afecten el mercado de Vehículos y por lo tanto modifiquen el valor de los mismos incluyendo pero limitándose a el valor de los combustibles, la tasa de impuestos de nuevos modelos o promociones especiales, la suspensión de producción o distribución de determinado modelo, publicidad positiva o negativa, percepciones, informes de desperfectos, cambios políticos o demográficos, desastres naturales y otras situaciones que tengan influencia sobre los valores de Vehículos.
        </div>

        <div class="vin-section" style="padding: 0;">
            <table style="width: 100%; border-collapse: separate; border-spacing: 0;">
                <tr style="background: #dbe7f3;">
                    <td style="width: 50%; padding: 1px 12px;">
                        <span class="vin-label">VIN</span>
                    </td>
                    <td style="width: 50%; padding: 1px 12px;">
                        <span class="vin-label"># Motor</span>
                    </td>
                </tr>
                <tr>
                    <td style="border-bottom: 2px solid #dbe7f3; padding: 4px 12px;">
                        <span>${esc(a.vin)}</span>
                    </td>
                    <td style="border-bottom: 2px solid #dbe7f3; padding: 4px 12px;">
                        <span>${esc(a.engine_number)}</span>
                    </td>
                </tr>
                <tr style="background: #dbe7f3;">
                    <td style="padding: 1px 12px;">
                        <span class="vin-label">VIN en tarjeta</span>
                    </td>
                    <td style="padding: 1px 12px;">
                        <span class="vin-label"># Motor en tarjeta</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 4px 12px;">
                        <span>${esc(a.vin_card)}</span>
                    </td>
                    <td style="padding: 4px 12px;">
                        <span>${esc(a.engine_number_card)}</span>
                    </td>
                </tr>
            </table>
        </div>

        <div class="validity-row">
            <div class="validity-stamp">
                VALIDO POR ${esc(a.validity_days ?? "")} DIAS O ${esc(a.validity_kms ?? "")} KMS
            </div>
        </div>
        </div>
    </div>
</body>
</html>`;
}

const APPRAISAL_COLUMNS = [
  "vehicle_appraisal_id",
  "appraisal_date",
  "brand",
  "vehicle_description",
  "model_year",
  "color",
  "plate_number",
  "mileage",
  "fuel_type",
  "engine_size",
  "origin",
  "vin",
  "engine_number",
  "applicant",
  "owner",
  "notes",
  "validity_days",
  "validity_kms",
  "extras",
  "vin_card",
  "engine_number_card",
  "appraisal_value_usd",
  "appraisal_value_trochez",
  "apprasail_value_lower_cost",
  "apprasail_value_bank",
  "apprasail_value_lower_bank",
  "bank_value_in_dollars",
  "cert",
  "referencia_original",
].join(",");

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
    .select(APPRAISAL_COLUMNS)
    .eq("vehicle_appraisal_id", id)
    .maybeSingle();
  if (error) return errorResponse(error.message, 500);
  if (!appraisal) return errorResponse("Appraisal not found", 404);

  const { data: deductions } = await supabase
    .from("appraisal_deductions")
    .select("appraisal_deductions_id, description, amount")
    .eq("vehicle_appraisal_id", id)
    .order("appraisal_deductions_id", { ascending: true });

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
