import Link from "next/link";
import { plans } from "@/lib/billing/plans";

import { Reveal } from "../_components/reveal";

export default function PricingPage() {
  return (
    <section className="px-5 py-24 md:py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal variant="stagger">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">Pricing</p>
          <h1 className="mt-4 max-w-3xl text-[clamp(2.4rem,5vw,4.25rem)] font-black leading-[0.98] tracking-[-0.045em] text-ink">
            Trial 7 días. Luego plan por organización.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-ink-2">
            Facturación por hospital/clínica. Uso médico real requiere contrato,
            validación local, privacidad, seguridad, aprobación regulatoria.
          </p>
        </Reveal>
        <Reveal variant="stagger" as="div" className="mt-12 grid gap-4 md:grid-cols-4">
          {plans.map((plan) => (
            <article key={plan.id} className="flex flex-col border-2 border-line bg-surface p-6 transition-all hover:-translate-y-1 hover:border-brand hover:shadow-xl hover:shadow-brand/10">
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
        </Reveal>
      </div>
    </section>
  );
}
