"use client";

import { useRef, useState, useTransition } from "react";
import type { AnalysisResponse } from "@heartscan/api-client";
import { analyzeImageAction, analyzeSignalAction } from "../actions";
import type { DiagnosticResponse } from "@/lib/analyze/diagnostic";
import type { Dict } from "@/lib/i18n/dictionaries";
import { PhotoResult, SignalResult } from "./analysis-result";

const MAX_BYTES = 10 * 1024 * 1024;
type Mode = "photo" | "signal";

export function AnalyzeClient({ t, result }: { t: Dict["analyze"]; result: Dict["result"] }) {
  // Signal-first: the 12-lead model is the calibrated copilot (AUROC ~0.88);
  // the photo path is a heuristic triage screen, so it isn't the default.
  const [mode, setMode] = useState<Mode>("signal");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<AnalysisResponse | null>(null);
  const [signal, setSignal] = useState<DiagnosticResponse | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function reset() {
    setError(null);
    setPhoto(null);
    setSignal(null);
  }

  async function loadSample() {
    setError(null);
    try {
      const res = await fetch("/ml-api/static/sample_ecg.png");
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      const f = new File([blob], "sample_ecg.png", { type: "image/png" });
      const dt = new DataTransfer();
      dt.items.add(f);
      if (inputRef.current) {
        inputRef.current.files = dt.files;
        setFileName(f.name);
      }
    } catch {
      setError(t.errSample);
    }
  }

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    reset();
    const form = e.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      setError(mode === "photo" ? t.errNoPhoto : t.errNoSignal);
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(t.errSize);
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
            {m === "signal" ? t.tabSignal : t.tabPhoto}
          </button>
        ))}
      </div>

      {mode === "photo" ? (
        <p className="border-2 border-warn/40 bg-warn-tint p-3 text-sm text-warn">
          {t.noteScreenA}
          <button
            type="button"
            onClick={() => {
              setMode("signal");
              reset();
              setFileName(null);
            }}
            className="font-semibold underline"
          >
            {t.tabSignal}
          </button>
          .
        </p>
      ) : (
        <p className="border-2 border-line bg-paper-2 p-3 text-sm text-ink-2">{t.noteCalibrated}</p>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f && inputRef.current) {
              inputRef.current.files = e.dataTransfer.files;
              setFileName(f.name);
            }
          }}
          className={`block cursor-pointer border-2 border-dashed px-6 py-10 text-center transition-colors focus-within:border-ink ${
            dragOver ? "border-ink bg-brand-tint/40" : "border-line-2 bg-surface hover:border-ink"
          }`}
        >
          <input
            ref={inputRef}
            name="file"
            type="file"
            aria-label={mode === "photo" ? t.dropPhotoLabel : t.dropSignalLabel}
            accept={mode === "photo" ? "image/png,image/jpeg,image/webp" : ".npy,.csv,text/csv"}
            className="sr-only"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
          <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-3">
            {mode === "photo" ? t.dropPhotoLabel : t.dropSignalLabel}
          </span>
          <span className="mt-2 block font-semibold text-ink">{fileName ?? t.dropPrompt}</span>
          <span className="mt-1 block text-xs text-ink-3">
            {mode === "photo" ? t.dropPhotoHint : t.dropSignalHint}
          </span>
        </label>

        {mode === "photo" && (
          <button
            type="button"
            onClick={loadSample}
            className="text-sm font-medium text-brand underline-offset-4 hover:underline"
          >
            {t.sample}
          </button>
        )}

        {mode === "signal" && (
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="hz" className="text-sm text-ink-2">
              {t.sampleRate}
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
            <span className="text-xs text-ink-3">{t.sampleRateHint}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={pending}
          className="bg-brand px-6 py-3 font-semibold text-white transition-colors hover:bg-brand-strong disabled:opacity-50"
        >
          {pending ? t.submitting : t.submit}
        </button>
      </form>

      {error && (
        <p className="border-2 border-crit/40 bg-crit-tint p-3 text-sm text-crit" role="alert">
          {error}
        </p>
      )}

      {photo && <PhotoResult data={photo} t={result} />}

      {signal && <SignalResult data={signal} t={result} />}
    </div>
  );
}
