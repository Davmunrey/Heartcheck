import type { AnalysisResponse } from "@heartscan/api-client";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";
import type { Dict } from "@/lib/i18n/dictionaries";

type ResultDict = Dict["result"];

/** Presentational result cards, shared by the live analyze flow and the
 *  saved-analysis detail page. Pure (no client state). */

export function PhotoResult({ data, t }: { data: AnalysisResponse; t: ResultDict }) {
  return (
    <div className="border-2 border-line bg-surface p-5">
      <div className="flex items-center justify-between">
        <p className="font-semibold">
          {t.statePhoto} {data.status}
        </p>
        <span className="border border-warn/40 bg-warn-tint px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-warn">
          {t.screenTag}
        </span>
      </div>
      <p className="mt-2 text-sm text-ink-2">{data.message}</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <dt className="text-ink-3">{t.bpm}</dt>
        <dd>{data.bpm ?? "—"}</dd>
        <dt className="text-ink-3">{t.confidence}</dt>
        <dd>{Math.round(data.confidence_score * 100)}%</dd>
        <dt className="text-ink-3">{t.class}</dt>
        <dd>{data.class_label}</dd>
      </dl>
      <p className="mt-4 text-xs text-ink-3">{data.disclaimer}</p>
    </div>
  );
}

export function SignalResult({ data, t }: { data: DiagnosticResponse; t: ResultDict }) {
  const relevant = [...data.findings]
    .filter((f) => f.positive || f.uncertain)
    .sort((a, b) => Number(b.positive) - Number(a.positive) || b.probability - a.probability);
  const normalCount = data.findings.length - relevant.length;

  return (
    <div className="border-2 border-line bg-surface p-5">
      <div className="flex items-center justify-between">
        <p className="font-semibold">{data.abnormal ? t.signalAbnormal : t.signalNormal}</p>
        <span
          className={`inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wide ${
            data.abnormal ? "border-warn/40 bg-warn-tint text-warn" : "border-ok/40 bg-ok-tint text-ok"
          }`}
        >
          <span className="size-1.5 rounded-full bg-current" />
          {data.abnormal ? t.chipReview : t.chipNormal}
        </span>
      </div>
      {data.requires_review && (
        <p className="mt-3 bg-brand-tint px-3 py-2 text-sm font-medium text-brand">{t.requiresReview}</p>
      )}
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-left text-ink-3">
            <th className="pb-1">{t.condition}</th>
            <th className="pb-1">{t.probability}</th>
            <th className="pb-1">{t.threshold}</th>
            <th className="pb-1">AUROC</th>
            <th className="pb-1"></th>
          </tr>
        </thead>
        <tbody>
          {relevant.map((f) => (
            <tr key={f.code} className={f.positive ? "font-medium text-ink" : "text-ink-2"}>
              <td className="py-1">{f.label}</td>
              <td className="py-1">{Math.round(f.probability * 100)}%</td>
              <td className="py-1 text-ink-3">{Math.round(f.threshold * 100)}%</td>
              <td className="py-1 text-ink-3">{f.auroc ? f.auroc.toFixed(2) : "—"}</td>
              <td className="py-1">
                {f.positive && (
                  <span className="border border-signal/40 bg-signal-tint px-1.5 py-0.5 text-xs text-signal-700">
                    {t.positive}
                  </span>
                )}
                {!f.positive && f.uncertain && (
                  <span className="border border-brand/40 bg-brand-tint px-1.5 py-0.5 text-xs text-brand">
                    {t.uncertain}
                  </span>
                )}
              </td>
            </tr>
          ))}
          {relevant.length === 0 && (
            <tr>
              <td colSpan={5} className="py-2 text-ink-2">
                {t.noneRelevant}
              </td>
            </tr>
          )}
          {normalCount > 0 && (
            <tr className="text-ink-3">
              <td colSpan={5} className="py-1 text-xs">
                {t.normalCount.replace("{n}", String(normalCount))}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-ink-3">
        {t.modelMeta
          .replace("{m}", data.model_version)
          .replace("{n}", String(data.findings.length))
          .replace("{a}", data.macro_auroc.toFixed(2))
          .replace("{leads}", String(data.n_leads))
          .replace("{hz}", String(data.sampling_rate_hz))}
      </p>
      <p className="mt-2 text-xs text-ink-3">{data.disclaimer}</p>
    </div>
  );
}
