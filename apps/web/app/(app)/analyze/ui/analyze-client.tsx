"use client";

import { useTransition, useState } from "react";
import { analyzeImageAction } from "../actions";
import type { AnalysisResponse } from "@heartscan/api-client";

const MAX_BYTES = 10 * 1024 * 1024;

export function AnalyzeClient() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const form = e.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      setError("Elige una imagen.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(`La imagen supera ${MAX_BYTES / (1024 * 1024)} MB.`);
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    startTransition(async () => {
      try {
        const data = await analyzeImageAction(fd);
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    });
  }

  return (
    <div className="mt-8 space-y-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <input
          name="file"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="block w-full text-sm"
        />
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
      {result && (
        <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <p className="font-semibold">Estado: {result.status}</p>
          <p className="mt-2 text-sm text-zinc-600">{result.message}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-zinc-500">BPM</dt>
            <dd>{result.bpm ?? "—"}</dd>
            <dt className="text-zinc-500">Confianza</dt>
            <dd>{Math.round(result.confidence_score * 100)}%</dd>
            <dt className="text-zinc-500">Clase</dt>
            <dd>{result.class_label}</dd>
          </dl>
          <p className="mt-4 text-xs text-zinc-500">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
