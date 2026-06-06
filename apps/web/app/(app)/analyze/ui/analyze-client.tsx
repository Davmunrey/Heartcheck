"use client";

import { useState, useTransition } from "react";
import type { AnalysisResponse } from "@heartscan/api-client";
import { analyzeImageAction, analyzeSignalAction } from "../actions";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";

const MAX_BYTES = 10 * 1024 * 1024;
type Mode = "photo" | "signal";

export function AnalyzeClient() {
  const [mode, setMode] = useState<Mode>("photo");
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
      <div className="inline-flex rounded-lg border border-zinc-200 bg-white p-1 text-sm">
        {(["photo", "signal"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              reset();
            }}
            className={`rounded-md px-3 py-1.5 ${
              mode === m ? "bg-zinc-900 text-white" : "text-zinc-600 hover:text-zinc-900"
            }`}
          >
            {m === "photo" ? "Foto (1 derivación)" : "Señal 12 derivaciones"}
          </button>
        ))}
      </div>

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
            <label className="block text-sm text-zinc-600">
              Frecuencia de muestreo (Hz)
              <input
                name="sampling_rate_hz"
                type="number"
                defaultValue={500}
                min={1}
                max={5000}
                className="ml-2 w-28 rounded border border-zinc-300 px-2 py-1"
              />
            </label>
            <p className="text-xs text-zinc-500">
              Sube una matriz 12×N (`.npy`) o CSV de 12 derivaciones. PTB-XL records100 = 100 Hz.
            </p>
          </div>
        )}
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-rose-600 px-4 py-2 text-white disabled:opacity-50"
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
        <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="font-semibold">Estado: {photo.status}</p>
          <p className="mt-2 text-sm text-zinc-600">{photo.message}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-zinc-500">BPM</dt>
            <dd>{photo.bpm ?? "—"}</dd>
            <dt className="text-zinc-500">Confianza</dt>
            <dd>{Math.round(photo.confidence_score * 100)}%</dd>
            <dt className="text-zinc-500">Clase</dt>
            <dd>{photo.class_label}</dd>
          </dl>
          <p className="mt-4 text-xs text-zinc-500">{photo.disclaimer}</p>
        </div>
      )}

      {signal && (
        <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
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
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-zinc-500">
                <th className="pb-1">Superclase</th>
                <th className="pb-1">Probabilidad</th>
                <th className="pb-1">Umbral</th>
                <th className="pb-1"></th>
              </tr>
            </thead>
            <tbody>
              {signal.findings.map((f) => (
                <tr key={f.code} className={f.positive ? "font-medium text-zinc-900" : "text-zinc-600"}>
                  <td className="py-1">{f.label}</td>
                  <td className="py-1">{Math.round(f.probability * 100)}%</td>
                  <td className="py-1 text-zinc-400">{Math.round(f.threshold * 100)}%</td>
                  <td className="py-1">
                    {f.positive && (
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-xs text-rose-700">
                        positivo
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-zinc-500">
            Modelo {signal.model_version} · {signal.n_leads} derivaciones · {signal.sampling_rate_hz} Hz
          </p>
          <p className="mt-2 text-xs text-zinc-500">{signal.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
