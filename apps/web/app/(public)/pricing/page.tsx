import Link from "next/link";
import { plans } from "@/lib/billing/plans";

export default function PricingPage() {
  return (
    <section className="px-5 py-20">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">Pricing</p>
        <h1 className="mt-3 max-w-3xl text-5xl font-black tracking-[-0.04em] text-ink">
          Trial 7 días. Luego plan por organización.
        </h1>
        <p className="mt-4 max-w-2xl text-ink-2">
          Facturación por hospital/clínica. Uso médico real requiere contrato,
          validación local, privacidad, seguridad, aprobación regulatoria.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-4">
          {plans.map((plan) => (
            <article key={plan.id} className="flex flex-col border-2 border-line bg-surface p-6">
              <h2 className="text-xl font-black text-ink">{plan.name}</h2>
              <p className="mt-2 text-3xl font-black text-ink">{plan.price}</p>
              <p className="mt-2 text-sm text-ink-2">{plan.tagline}</p>
              <p className="mt-4 inline-flex self-start bg-brand-tint px-3 py-1 text-sm font-semibold text-brand">
                {plan.quota}
              </p>
              <ul className="mt-5 space-y-2 text-sm text-ink-2">
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <span className="text-brand">✓</span> {feature}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.id === "enterprise" ? "/enterprise" : "/sign-up"}
                className="mt-6 inline-flex self-start bg-brand px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-strong"
              >
                {plan.id === "enterprise" ? "Contactar" : "Empezar"}
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
