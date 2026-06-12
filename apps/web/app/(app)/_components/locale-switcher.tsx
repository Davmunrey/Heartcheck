"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { setLocaleAction } from "@/lib/i18n/actions";
import type { Locale } from "@/lib/i18n/dictionaries";

export function LocaleSwitcher({ locale }: { locale: Locale }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function set(next: Locale) {
    if (next === locale) return;
    startTransition(async () => {
      await setLocaleAction(next);
      router.refresh();
    });
  }

  return (
    <div className="inline-flex border-2 border-line font-mono text-[11px] uppercase">
      {(["es", "en"] as const).map((l) => (
        <button
          key={l}
          type="button"
          disabled={pending}
          onClick={() => set(l)}
          aria-pressed={l === locale}
          className={`px-2 py-1 transition-colors ${
            l === locale ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}
