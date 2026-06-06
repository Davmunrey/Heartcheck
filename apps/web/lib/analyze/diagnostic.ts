// 12-lead diagnostic (signal wedge) response — mirrors the FastAPI
// DiagnosticResponse schema (apps/ml-api/app/schemas/diagnostic.py).
// Kept local to the web app to avoid a codegen round-trip on the shared
// api-client package; validated defensively at the trust boundary.

export interface DiagnosticFinding {
  code: string;
  label: string;
  probability: number;
  positive: boolean;
  threshold: number;
}

export interface DiagnosticResponse {
  abnormal: boolean;
  findings: DiagnosticFinding[];
  n_leads: number;
  sampling_rate_hz: number;
  model_version: string;
  pipeline_version: string;
  request_id: string;
  disclaimer: string;
  analysis_limit: string[];
}

export class DiagnosticParseError extends Error {}

function num(v: unknown, field: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new DiagnosticParseError(`Campo numérico inválido: ${field}`);
  }
  return v;
}

export function parseDiagnosticResponse(raw: unknown): DiagnosticResponse {
  if (typeof raw !== "object" || raw === null) {
    throw new DiagnosticParseError("Respuesta vacía del servicio de análisis.");
  }
  const o = raw as Record<string, unknown>;
  if (!Array.isArray(o.findings)) {
    throw new DiagnosticParseError("Respuesta sin findings.");
  }
  const findings: DiagnosticFinding[] = o.findings.map((f) => {
    const x = f as Record<string, unknown>;
    return {
      code: String(x.code ?? ""),
      label: String(x.label ?? x.code ?? ""),
      probability: num(x.probability, "probability"),
      positive: Boolean(x.positive),
      threshold: num(x.threshold, "threshold"),
    };
  });
  return {
    abnormal: Boolean(o.abnormal),
    findings,
    n_leads: typeof o.n_leads === "number" ? o.n_leads : 12,
    sampling_rate_hz: typeof o.sampling_rate_hz === "number" ? o.sampling_rate_hz : 0,
    model_version: String(o.model_version ?? "unknown"),
    pipeline_version: String(o.pipeline_version ?? ""),
    request_id: String(o.request_id ?? ""),
    disclaimer: String(o.disclaimer ?? ""),
    analysis_limit: Array.isArray(o.analysis_limit) ? o.analysis_limit.map(String) : [],
  };
}
