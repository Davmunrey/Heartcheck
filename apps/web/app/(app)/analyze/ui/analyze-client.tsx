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
      <div className="inline-flex rounded-lg border border-line bg-white p-1 text-sm">
        {(["signal", "photo"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              reset();
            }}
            className={`rounded-md px-3 py-1.5 ${
              mode === m ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
            }`}
          >
            {m === "signal" ? "Señal 12 derivaciones" : "Foto (cribado)"}
          </button>
        ))}
      </div>

      {mode === "photo" ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Cribado orientativo.</strong> La lectura por foto usa un clasificador
          heurístico de 1 derivación (no un modelo diagnóstico entrenado), pensado para
          un triaje rápido. Para la interpretación calibrada de 27 afecciones, usa{" "}
          <button
            type="button"
            onClick={() => {
              setMode("signal");
              reset();
            }}
            className="font-semibold underline"
          >
            Señal 12 derivaciones
          </button>
          .
        </p>
      ) : (
        <p className="rounded-lg border border-line bg-paper-2 p-3 text-sm text-ink-2">
          <strong>Copiloto calibrado.</strong> Modelo de 12 derivaciones · 27 afecciones,
          umbrales calibrados y AUROC por hallazgo. Apoyo a la decisión clínica —
          requiere revisión médica, no es un diagnóstico autónomo.
        </p>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        {mode === "photo" ? (
          <input
            name="file"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="block w-full text-sm"
          />
        ) : (
          <div className="space-y-3">
            <input name="file" type="file" accept=".npy,.csv,text/csv" className="block w-full text-sm" />
            <label className="block text-sm text-ink-2">
              Frecuencia de muestreo (Hz)
              <input
                name="sampling_rate_hz"
                type="number"
                defaultValue={500}
                min={1}
                max={5000}
                className="ml-2 w-28 rounded border border-line-2 px-2 py-1"
              />
            </label>
            <p className="text-xs text-ink-3">
              Sube una matriz 12×N (`.npy`) o CSV de 12 derivaciones. PTB-XL records100 = 100 Hz.
            </p>
          </div>
        )}
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-brand px-4 py-2 text-white disabled:opacity-50"
        >
          {pending ? "Analizando…" : "Analizar"}
        </button>
      </form>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800" role="alert">
          {error}
        </p>
      )}

      {photo && (
        <div className="rounded-lg border border-line bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="font-semibold">Estado: {photo.status}</p>
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
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
        <div className="rounded-lg border border-line bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="font-semibold">
              {signal.abnormal ? "Hallazgos a revisar" : "Sin hallazgos sobre el umbral"}
            </p>
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${
                signal.abnormal ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
              }`}
            >
              {signal.abnormal ? "review" : "normal range"}
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
