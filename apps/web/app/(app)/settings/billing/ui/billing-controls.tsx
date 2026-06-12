"use client";

import { useState, useTransition } from "react";

export function BillingControls({ planId }: { planId?: string }) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);

  function post(path: string, body?: unknown) {
    setMessage(null);
    startTransition(async () => {
      const res = await fetch(path, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
        return;
      }
      setMessage(data.message ?? data.error ?? "Sin respuesta");
    });
  }

  return (
    <div className="space-y-2">
      {planId ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => post("/api/billing/checkout", { planId })}
          className="w-full bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-strong disabled:opacity-50"
        >
          {pending ? "Redirigiendo…" : "Suscribirse"}
        </button>
      ) : (
        <button
          type="button"
          disabled={pending}
          onClick={() => post("/api/billing/portal")}
          className="border-2 border-ink px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-ink hover:text-white disabled:opacity-50"
        >
          {pending ? "Abriendo…" : "Abrir portal Stripe"}
        </button>
      )}
      {message && <p className="text-sm text-ink-2">{message}</p>}
    </div>
  );
}
