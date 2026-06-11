import Link from "next/link";

import { EcgHero } from "./_components/ecg-hero";
import { Reveal } from "./_components/reveal";

const stats = [
  ["27", "afecciones detectadas", "ritmo + diagnóstico, no 5 categorías"],
  ["0.88", "AUROC macro", "discriminación a nivel clínico"],
  ["43k", "ECG de entrenamiento", "PTB-XL + CinC2020 multi-fuente"],
];

const pillars = [
  {
    kicker: "Lectura completa",
    title: "Detecta el ritmo, no solo la morfología.",
    body: "Fibrilación auricular, flutter, taquicardia y bradicardia sinusal, extrasístoles auriculares y ventriculares — además de bloqueos, ST/T, hipertrofia e infarto. El informe que un cardiólogo espera.",
    chips: ["AF 0.96", "Flutter 0.95", "PVC 0.96", "RBBB 0.98"],
  },
  {
    kicker: "Confianza, no caja negra",
    title: "Probabilidades calibradas y abstención.",
    body: "Cada hallazgo trae su AUROC y un umbral. Cuando el modelo duda, lo dice y escala a revisión humana — diseñado como copiloto clínico, nunca como diagnóstico autónomo.",
    chips: ["AUROC por clase", "Abstención conformal", "Human-in-the-loop"],
  },
  {
    kicker: "Listo para empresa",
    title: "Aislamiento por hospital desde el día cero.",
    body: "Tenant por organización con Clerk + RLS de Supabase, audit log append-only, almacenamiento privado, JWT y rate limits. Un solo dominio, cero PHI en logs.",
    chips: ["RLS por org", "Audit chain", "API + consola"],
  },
];

const affections = [
  "Fibrilación auricular", "Flutter auricular", "Taquicardia sinusal", "Bradicardia sinusal",
  "Extrasístole ventricular", "Extrasístole auricular", "Bloqueo de rama izq.", "Bloqueo de rama der.",
  "Bloqueo AV 1.º grado", "Hemibloqueo ant. izq.", "Hipertrofia ventricular", "Infarto de miocardio",
  "Cambios ST/T", "Inversión onda T", "Eje izquierdo", "QT prolongado",
];

export default function LandingPage() {
  return (
    <>
      {/* ===== HERO ===== */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="orb-a absolute -right-24 top-0 h-[28rem] w-[28rem] rounded-full bg-brand/15 blur-[110px]" />
          <div className="orb-b absolute -left-24 top-40 h-[24rem] w-[24rem] rounded-full bg-signal/10 blur-[110px]" />
        </div>
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-14 md:grid-cols-[1.05fr_0.95fr] md:pb-28 md:pt-20">
          <Reveal variant="stagger">
            <p className="inline-flex items-center gap-2 border-2 border-ink/10 px-3 py-1 text-sm text-ink-2">
              <span className="size-1.5 rounded-full bg-signal" /> Copiloto ECG · 27 afecciones
            </p>
            <h1 className="mt-6 text-[clamp(2.8rem,7vw,5.5rem)] font-black leading-[0.92] tracking-[-0.05em]">
              <span className="text-shimmer">El ECG,</span>
              <br />
              leído al completo.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-ink-2">
              Axis interpreta un electrocardiograma de 12 derivaciones y devuelve un
              informe de 27 afecciones — ritmo y diagnóstico — con probabilidades
              calibradas. Para equipos clínicos. No sustituye criterio médico.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                href="/sign-up"
                className="group inline-flex items-center gap-2 bg-brand px-7 py-3.5 font-semibold text-white shadow-xl shadow-brand/25 transition-all hover:bg-brand-strong hover:shadow-2xl hover:shadow-brand/30"
              >
                Empezar trial 7 días
                <span className="transition-transform group-hover:translate-x-1">→</span>
              </Link>
              <Link href="/copilot" className="font-semibold text-ink underline-offset-4 hover:text-brand hover:underline">
                Ver cómo funciona
              </Link>
            </div>
          </Reveal>
          <Reveal variant="reveal reveal-scale">
            <EcgHero />
          </Reveal>
        </div>
      </section>

      {/* ===== STATS ===== */}
      <section className="border-y-2 border-line bg-surface">
        <Reveal variant="stagger" as="div" className="mx-auto grid max-w-7xl gap-px px-5 py-14 sm:grid-cols-3">
          {stats.map(([big, label, sub]) => (
            <div key={label} className="px-4 text-center sm:text-left">
              <div className="text-5xl font-black tracking-tight text-ink md:text-6xl">{big}</div>
              <div className="mt-2 font-semibold text-ink">{label}</div>
              <div className="mt-1 text-sm text-ink-3">{sub}</div>
            </div>
          ))}
        </Reveal>
      </section>

      {/* ===== PILLARS ===== */}
      <div className="mx-auto max-w-7xl px-5">
        {pillars.map((p, i) => (
          <Reveal key={p.title} className="grid items-center gap-10 border-b-2 border-line py-20 md:grid-cols-2 md:py-28">
            <div className={i % 2 ? "md:order-2" : ""}>
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">{p.kicker}</p>
              <h2 className="mt-4 text-[clamp(2rem,4vw,3.25rem)] font-black leading-[1.02] tracking-[-0.04em] text-ink">
                {p.title}
              </h2>
              <p className="mt-5 max-w-lg text-lg leading-8 text-ink-2">{p.body}</p>
              <div className="mt-7 flex flex-wrap gap-2">
                {p.chips.map((c) => (
                  <span key={c} className="bg-brand-tint px-3 py-1 font-mono text-sm text-brand">{c}</span>
                ))}
              </div>
            </div>
            <div className={i % 2 ? "md:order-1" : ""}>
              <div className="relative aspect-[4/3] overflow-hidden border-2 border-line bg-scope">
                <div className="absolute inset-0 opacity-20 [background:repeating-linear-gradient(0deg,rgba(61,123,255,.5)_0_1px,transparent_1px_20px),repeating-linear-gradient(90deg,rgba(61,123,255,.5)_0_1px,transparent_1px_20px)]" />
                <div className={`absolute h-24 w-24 rounded-full blur-2xl ${i % 2 ? "right-8 top-8 bg-signal/40 orb-b" : "left-8 bottom-8 bg-brand/40 orb-a"}`} />
                <svg viewBox="0 0 400 300" className="relative h-full w-full" preserveAspectRatio="none">
                  <path
                    d="M0 160 l60 0 q8 0 12 -14 q4 -14 9 0 l7 0 l6 42 l7 -90 l7 64 l7 -16 q7 0 12 18 q4 14 9 0 l180 0"
                    className="ecg-path" fill="none" stroke="var(--brand-bright)" strokeWidth="2.5" strokeLinejoin="round"
                  />
                </svg>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      {/* ===== 27 AFFECTIONS ===== */}
      <section className="mx-auto max-w-7xl px-5 py-20 md:py-28">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand">Cobertura</p>
          <h2 className="mt-4 max-w-3xl text-[clamp(2rem,4vw,3.25rem)] font-black leading-[1.02] tracking-[-0.04em]">
            Un panel, no un semáforo.
          </h2>
        </Reveal>
        <Reveal variant="stagger" as="ul" className="mt-10 grid grid-cols-2 gap-px bg-line sm:grid-cols-3 lg:grid-cols-4">
          {affections.map((a) => (
            <li key={a} className="flex items-center gap-2 bg-surface px-4 py-4 text-sm font-medium text-ink transition-colors hover:bg-paper-2">
              <span className="size-1.5 shrink-0 bg-brand" />
              {a}
            </li>
          ))}
          <li className="flex items-center bg-brand px-4 py-4 text-sm font-semibold text-white">+ 11 más</li>
        </Reveal>
      </section>

      {/* ===== DARK ENTERPRISE BAND ===== */}
      <section className="relative overflow-hidden bg-scope text-scope-ink">
        <div className="orb-a absolute -left-20 top-10 h-72 w-72 rounded-full bg-brand/20 blur-[100px]" />
        <Reveal className="relative mx-auto max-w-7xl px-5 py-24 md:py-32">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">Enterprise</p>
          <h2 className="mt-4 max-w-4xl text-[clamp(2.2rem,5vw,4rem)] font-black leading-[1.0] tracking-[-0.045em] text-white">
            Seguridad antes que crecimiento.
          </h2>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-scope-ink/75">
            Aislamiento por organización, audit log hash-chain, almacenamiento privado,
            firmas de webhook y cero secretos en cliente. Listo para evaluación
            DPA/BAA y despliegue privado.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/enterprise" className="bg-white px-7 py-3.5 font-semibold text-scope transition-colors hover:bg-scope-ink">
              Hablar con ventas
            </Link>
            <Link href="/security" className="border-2 border-white/20 px-7 py-3.5 font-semibold text-white transition-colors hover:border-white">
              Ver seguridad
            </Link>
          </div>
        </Reveal>
      </section>

      {/* ===== FINAL CTA ===== */}
      <section className="mx-auto max-w-7xl px-5 py-24 text-center md:py-32">
        <Reveal variant="reveal reveal-scale">
          <h2 className="mx-auto max-w-4xl text-[clamp(2.4rem,6vw,4.5rem)] font-black leading-[0.98] tracking-[-0.05em]">
            Empieza a leer ECG
            <br />
            <span className="text-brand">como un equipo de élite.</span>
          </h2>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link
              href="/sign-up"
              className="group inline-flex items-center gap-2 bg-brand px-8 py-4 text-lg font-semibold text-white shadow-xl shadow-brand/25 transition-all hover:bg-brand-strong"
            >
              Empezar trial 7 días
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
            <Link href="/pricing" className="border-2 border-ink/15 px-8 py-4 text-lg font-semibold text-ink transition-colors hover:border-brand hover:text-brand">
              Ver planes
            </Link>
          </div>
          <p className="mt-6 text-sm text-ink-3">No diagnóstico autónomo · revisión humana · uso clínico requiere validación local.</p>
        </Reveal>
      </section>
    </>
  );
}
