"use client";

import { useState, useTransition } from "react";
import type { AnalysisResponse } from "@heartscan/api-client";
import { analyzeImageAction, analyzeSignalAction } from "../actions";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";

const MAX_BYTES = 10 * 1024 * 1024;
type Mode = "photo" | "signal";

export function AnalyzeClient() {
  // Signal-first: the 12-lead model is the calibrated copilot (AUROC ~0.88);
  // the photo path is a heuristic triage screen, so it isn't the default.
  const [mode, setMode] = useState<Mode>("signal");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<AnalysisResponse | null>(null);
  const [signal, setSignal] = useState<DiagnosticResponse | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function reset() {
    setError(null);
    setPhoto(null);
    setSignal(null);
  }

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    reset();
    const form = e.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      setError(mode === "photo" ? "Elige una imagen." : "Elige una señal (.npy o .csv).");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(`El archivo supera ${MAX_BYTES / (1024 * 1024)} MB.`);
      return;
    }
    const fd = new FormData();
    fd.append("file", file);

    startTransition(async () => {
      try {
        if (mode === "photo") {
          setPhoto(await analyzeImageAction(fd));
        } else {
          const hz = (form.elements.namedItem("sampling_rate_hz") as HTMLInputElement)?.value;
          fd.append("sampling_rate_hz", hz || "500");
          setSignal(await analyzeSignalAction(fd));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    });
  }

  return (
    <div className="mt-8 space-y-6">
      <div className="inline-flex border-2 border-line bg-surface p-1 text-sm">
        {(["signal", "photo"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              reset();
              setFileName(null);
            }}
            className={`px-4 py-2 font-medium transition-colors ${
              mode === m ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
            }`}
          >
            {m === "signal" ? "Señal 12 derivaciones" : "Foto (cribado)"}
          </button>
        ))}
      </div>

      {mode === "photo" ? (
        <p className="border-2 border-warn/40 bg-warn-tint p-3 text-sm text-warn">
          <strong className="font-bold">Cribado orientativo.</strong> La lectura por foto usa un
          clasificador heurístico de 1 derivación (no un modelo diagnóstico entrenado), pensado para
          un triaje rápido. Para la interpretación calibrada de 27 afecciones, usa{" "}
          <button
            type="button"
            onClick={() => {
              setMode("signal");
              reset();
              setFileName(null);
            }}
            className="font-semibold underline"
          >
            Señal 12 derivaciones
          </button>
          .
        </p>
      ) : (
        <p className="border-2 border-line bg-paper-2 p-3 text-sm text-ink-2">
          <strong className="font-bold text-ink">Copiloto calibrado.</strong> Modelo de 12 derivaciones · 27 afecciones,
          umbrales calibrados y AUROC por hallazgo. Apoyo a la decisión clínica —
          requiere revisión médica, no es un diagnóstico autónomo.
        </p>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block cursor-pointer border-2 border-dashed border-line-2 bg-surface px-6 py-10 text-center transition-colors hover:border-ink">
          <input
            name="file"
            type="file"
            accept={mode === "photo" ? "image/png,image/jpeg,image/webp" : ".npy,.csv,text/csv"}
            className="sr-only"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
          <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-3">
            {mode === "photo" ? "Imagen de ECG" : "Señal 12 derivaciones"}
          </span>
          <span className="mt-2 block font-semibold text-ink">
            {fileName ?? "Selecciona un archivo"}
          </span>
          <span className="mt-1 block text-xs text-ink-3">
            {mode === "photo"
              ? "PNG · JPG · WebP — máx. 10 MB"
              : ".npy (matriz 12×N) o .csv — máx. 10 MB"}
          </span>
        </label>

        {mode === "signal" && (
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="hz" className="text-sm text-ink-2">
              Frecuencia de muestreo (Hz)
            </label>
            <input
              id="hz"
              name="sampling_rate_hz"
              type="number"
              defaultValue={500}
              min={1}
              max={5000}
              className="w-28 border-2 border-line-2 px-3 py-1.5 text-sm focus:border-ink focus:outline-none"
            />
            <span className="text-xs text-ink-3">PTB-XL records100 = 100 Hz</span>
          </div>
        )}

        <button
          type="submit"
          disabled={pending}
          className="bg-brand px-6 py-3 font-semibold text-white transition-colors hover:bg-brand-strong disabled:opacity-50"
        >
          {pending ? "Analizando…" : "Analizar"}
        </button>
      </form>

      {error && (
        <p className="border-2 border-crit/40 bg-crit-tint p-3 text-sm text-crit" role="alert">
          {error}
        </p>
      )}

      {photo && (
        <div className="border-2 border-line bg-surface p-5">
          <div className="flex items-center justify-between">
            <p className="font-semibold">Estado: {photo.status}</p>
            <span className="border border-warn/40 bg-warn-tint px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-warn">
              cribado heurístico
            </span>
          </div>
          <p className="mt-2 text-sm text-ink-2">{photo.message}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-ink-3">BPM</dt>
            <dd>{photo.bpm ?? "—"}</dd>
            <dt className="text-ink-3">Confianza</dt>
            <dd>{Math.round(photo.confidence_score * 100)}%</dd>
            <dt className="text-ink-3">Clase</dt>
            <dd>{photo.class_label}</dd>
          </dl>
          <p className="mt-4 text-xs text-ink-3">{photo.disclaimer}</p>
        </div>
      )}

      {signal && (
        <div className="border-2 border-line bg-surface p-5">
          <div className="flex items-center justify-between">
            <p className="font-semibold">
              {signal.abnormal ? "Hallazgos a revisar" : "Sin hallazgos sobre el umbral"}
            </p>
            <span
              className={`inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wide ${
                signal.abnormal ? "border-warn/40 bg-warn-tint text-warn" : "border-ok/40 bg-ok-tint text-ok"
              }`}
            >
              <span className="size-1.5 rounded-full bg-current" />
              {signal.abnormal ? "revisar" : "rango normal"}
            </span>
          </div>
          {signal.requires_review && (
            <p className="mt-3 bg-brand-tint px-3 py-2 text-sm font-medium text-brand">
              Requiere revisión médica (hallazgo positivo o incierto).
            </p>
          )}
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-ink-3">
                <th className="pb-1">Afección</th>
                <th className="pb-1">Probabilidad</th>
                <th className="pb-1">Umbral</th>
                <th className="pb-1">AUROC</th>
                <th className="pb-1"></th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const relevant = [...signal.findings]
                  .filter((f) => f.positive || f.uncertain)
                  .sort((a, b) => Number(b.positive) - Number(a.positive) || b.probability - a.probability);
                const normalCount = signal.findings.length - relevant.length;
                return (
                  <>
                    {relevant.map((f) => (
                      <tr key={f.code} className={f.positive ? "font-medium text-ink" : "text-ink-2"}>
                        <td className="py-1">{f.label}</td>
                        <td className="py-1">{Math.round(f.probability * 100)}%</td>
                        <td className="py-1 text-ink-3">{Math.round(f.threshold * 100)}%</td>
                        <td className="py-1 text-ink-3">{f.auroc ? f.auroc.toFixed(2) : "—"}</td>
                        <td className="py-1">
                          {f.positive && (
                            <span className="rounded bg-signal-tint px-1.5 py-0.5 text-xs text-signal-700">
                              positivo
                            </span>
                          )}
                          {!f.positive && f.uncertain && (
                            <span className="rounded bg-brand-tint px-1.5 py-0.5 text-xs text-brand">
                              incierto
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {relevant.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-2 text-ink-2">
                          Sin hallazgos positivos ni inciertos.
                        </td>
                      </tr>
                    )}
                    {normalCount > 0 && (
                      <tr className="text-ink-3">
                        <td colSpan={5} className="py-1 text-xs">
                          + {normalCount} afecciones en rango normal (no detectadas).
                        </td>
                      </tr>
                    )}
                  </>
                );
              })()}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-ink-3">
            Modelo {signal.model_version} · {signal.findings.length} afecciones evaluadas · AUROC {signal.macro_auroc.toFixed(2)} · {signal.n_leads} derivaciones · {signal.sampling_rate_hz} Hz
          </p>
          <p className="mt-2 text-xs text-ink-3">{signal.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
