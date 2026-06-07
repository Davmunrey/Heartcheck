import Link from "next/link";

const assurances = [
  "Tenant por hospital con Clerk Organizations + Supabase RLS",
  "Trial 7 días, cuotas por plan, audit log append-only",
  "No diagnóstico autónomo: copilot clínico con revisión humana",
  "API + web console listas para integración B2B",
];

const workflows = [
  "Ingesta ECG",
  "Quality gate",
  "Inferencia ML",
  "Revisión médica",
  "PDF/API report",
  "Feedback → training queue",
];

const scopeMetrics = ["Quality 92%", "NORM 0.98", "CD 0.89"];

export default function LandingPage() {
  return (
    <>
      <section className="relative mx-auto grid max-w-7xl gap-10 px-5 py-16 md:grid-cols-[1.05fr_0.95fr] md:py-24">
        <div className="absolute -right-28 top-12 h-72 w-72 rounded-full bg-brand/20 blur-3xl" />
        <div className="absolute -left-32 bottom-0 h-80 w-80 rounded-full bg-signal/15 blur-3xl" />
        <div className="relative">
          <p className="mb-5 inline-flex border-2 border-ink/15 px-3 py-1 text-sm text-ink-2">
            SaaS ECG para hospitales, clínicas, aseguradoras, telemedicina
          </p>
          <h1 className="max-w-4xl text-5xl font-black leading-[0.95] tracking-[-0.05em] md:text-7xl">
            Copilot ECG seguro para equipos clínicos.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-ink-2">
            Sube ECG, valida calidad, genera ayuda interpretativa, exporta
            informe, deja trazabilidad. Diseñado para médicos. No sustituye
            criterio clínico.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/sign-up"
              className="bg-brand px-6 py-3 font-semibold text-white shadow-lg shadow-brand/20 transition-colors hover:bg-brand-strong"
            >
              Empezar trial 7 días
            </Link>
            <Link
              href="/copilot"
              className="border-2 border-ink/20 px-6 py-3 font-semibold text-ink transition-colors hover:border-brand hover:text-brand"
            >
              Ver copilot
            </Link>
          </div>
        </div>
        <div className="relative bg-scope p-5 text-scope-ink shadow-2xl">
          <div className="bg-scope-2 p-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 text-sm">
              <span className="font-mono">ECG case · QRS-2049</span>
              <span className="bg-signal px-2 py-1 text-xs font-semibold text-white">review needed</span>
            </div>
            <div className="mt-6 h-40 bg-[repeating-linear-gradient(0deg,rgba(61,123,255,.16)_0_1px,transparent_1px_16px),repeating-linear-gradient(90deg,rgba(61,123,255,.16)_0_1px,transparent_1px_16px)]" />
            <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
              {scopeMetrics.map((item) => (
                <div key={item} className="bg-white/5 p-3 font-mono text-xs">{item}</div>
              ))}
            </div>
            <ol className="mt-5 space-y-2 text-sm text-scope-ink/75">
              {workflows.map((step, index) => (
                <li key={step} className="flex gap-3">
                  <span className="font-mono text-brand-bright">0{index + 1}</span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-20 md:grid-cols-4">
        {assurances.map((item) => (
          <div key={item} className="border-2 border-line bg-surface p-5">
            <p className="text-sm font-semibold leading-6 text-ink">{item}</p>
          </div>
        ))}
      </section>

      <section className="bg-scope px-5 py-16 text-scope-ink">
        <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">Enterprise ready</p>
            <h2 className="mt-3 text-4xl font-black tracking-tight text-white">Seguridad antes que crecimiento.</h2>
          </div>
          <div className="bg-white/5 p-6">
            <h3 className="font-bold text-white">Cyber + compliance</h3>
            <p className="mt-3 text-sm leading-6 text-scope-ink/70">
              RLS por organización, JWT Clerk, audit chain, private storage,
              rate limits, no secretos en cliente, data retention.
            </p>
          </div>
          <div className="bg-white/5 p-6">
            <h3 className="font-bold text-white">Workflow médico</h3>
            <p className="mt-3 text-sm leading-6 text-scope-ink/70">
              Orquestación tipo Temporal: activities idempotentes para pago,
              análisis, reportes; workflows deterministas para estados.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
