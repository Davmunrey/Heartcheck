"use client";

import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-signal">Error</p>
      <h1 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.04]">Algo salió mal</h1>
      <p className="mt-3 text-ink-2">
        Ha ocurrido un error inesperado. Vuelve a intentarlo; si persiste, contacta soporte.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        Reintentar
      </button>
    </div>
  );
}
