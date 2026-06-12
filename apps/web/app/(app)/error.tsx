"use client";

import { useEffect } from "react";
import { dictionaries } from "@/lib/i18n/dictionaries";

function localeFromCookie(): "es" | "en" {
  if (typeof document === "undefined") return "es";
  return document.cookie.split("; ").find((c) => c.startsWith("locale="))?.split("=")[1] === "en"
    ? "en"
    : "es";
}

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

  const s = dictionaries[localeFromCookie()].states;

  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-signal">{s.errorEyebrow}</p>
      <h1 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.04]">{s.errorTitle}</h1>
      <p className="mt-3 text-ink-2">{s.errorBody}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 inline-flex bg-brand px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-strong"
      >
        {dictionaries[localeFromCookie()].common.retry}
      </button>
    </div>
  );
}
