import { BillingControls } from "./ui/billing-controls";
import { plans } from "@/lib/billing/plans";
import { getBillingStatus } from "@/lib/billing/status";

const FEATURED = "hospital";

export default async function BillingSettingsPage() {
  const status = await getBillingStatus();
  const paid = plans.filter((p) => p.id !== "trial");

  return (
    <div className="mx-auto max-w-5xl px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">Facturación</p>
      <h1 className="mt-3 text-[clamp(2rem,4vw,3rem)] leading-[1.02]">Planes y suscripción</h1>
      <p className="mt-3 max-w-xl text-ink-2">
        Trial de 7 días, checkout y portal de cliente con Stripe. Cambia o cancela cuando quieras.
      </p>

      {/* Current plan strip */}
      <div className="mt-8 flex flex-wrap items-center gap-x-10 gap-y-4 border-2 border-line bg-surface px-6 py-5">
        {[
          ["Plan actual", status.plan],
          ["Estado", status.subscriptionStatus],
          ["Trial restante", status.trialDaysLeft != null ? `${status.trialDaysLeft} días` : "—"],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-3">{k}</p>
            <p className="mt-1 font-semibold capitalize text-ink">{v}</p>
          </div>
        ))}
        <div className="ml-auto">
          <BillingControls />
        </div>
      </div>

      {/* Plans */}
      <div className="mt-10 grid gap-5 md:grid-cols-3">
        {paid.map((plan) => {
          const featured = plan.id === FEATURED;
          return (
            <div
              key={plan.id}
              className={`flex flex-col border-2 bg-surface p-6 transition-colors ${
                featured ? "border-ink" : "border-line hover:border-ink"
              }`}
            >
              {featured && <div className="-mx-6 -mt-6 mb-6 h-1 bg-signal" />}
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-ink">{plan.name}</h2>
                {featured && (
                  <span className="bg-signal px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-white">
                    Popular
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-ink-2">{plan.tagline}</p>

              <p className="mt-5 font-mono text-2xl font-semibold tracking-tight text-ink">{plan.price}</p>
              <p className="mt-1 text-sm text-ink-3">{plan.quota}</p>

              <ul className="mt-5 space-y-2 text-sm text-ink-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <span className="mt-0.5 text-signal">→</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-6 flex-1" />
              <BillingControls planId={plan.id} />
            </div>
          );
        })}
      </div>

      <p className="mt-6 text-xs leading-5 text-ink-3">
        El uso clínico real requiere validación local, contrato y revisión regulatoria (DPA/BAA).
      </p>
    </div>
  );
}
