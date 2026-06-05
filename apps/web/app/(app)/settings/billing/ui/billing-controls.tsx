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
    <div className="mt-4 space-y-2">
      {planId ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => post("/api/billing/checkout", { planId })}
          className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Checkout {planId}
        </button>
      ) : (
        <button
          type="button"
          disabled={pending}
          onClick={() => post("/api/billing/portal")}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Abrir portal Stripe
        </button>
      )}
      {message && <p className="text-sm text-zinc-600">{message}</p>}
    </div>
  );
}
