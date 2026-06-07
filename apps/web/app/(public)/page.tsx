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

export default function LandingPage() {
  return (
    <div className="min-h-full overflow-hidden bg-[#f4f0e8] text-[#17211f]">
      <header className="border-b border-[#17211f]/10 bg-[#f4f0e8]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5">
          <div className="flex items-center gap-3 font-semibold tracking-tight">
            <span className="grid size-9 place-items-center rounded-full bg-[#17211f] text-[#f4f0e8]">
              ECG
            </span>
            <span>Axis</span>
            <span className="rounded-full bg-[#d7ff63] px-2 py-0.5 text-xs text-[#17211f]">
              clinical copilot beta
            </span>
          </div>
          <nav className="hidden items-center gap-5 text-sm md:flex">
            <Link href="/copilot" className="hover:text-[#b54708]">Copilot</Link>
            <Link href="/security" className="hover:text-[#b54708]">Seguridad</Link>
            <Link href="/pricing" className="hover:text-[#b54708]">Planes</Link>
            <Link href="/faq" className="hover:text-[#b54708]">FAQ</Link>
            <Link href="/sign-in" className="hover:text-[#b54708]">Entrar</Link>
            <Link
              href="/sign-up"
              className="rounded-full bg-[#17211f] px-4 py-2 text-[#f4f0e8] hover:bg-[#2b3935]"
            >
              Trial 7 días
            </Link>
          </nav>
        </div>
      </header>
      <main>
        <section className="relative mx-auto grid max-w-7xl gap-10 px-5 py-16 md:grid-cols-[1.05fr_0.95fr] md:py-24">
          <div className="absolute -right-28 top-12 h-72 w-72 rounded-full bg-[#ff7a59]/30 blur-3xl" />
          <div className="absolute -left-32 bottom-0 h-80 w-80 rounded-full bg-[#85d7ff]/30 blur-3xl" />
          <div className="relative">
            <p className="mb-5 inline-flex rounded-full border border-[#17211f]/15 px-3 py-1 text-sm">
              SaaS ECG para hospitales, clínicas, aseguradoras, telemedicina
            </p>
            <h1 className="max-w-4xl text-5xl font-black leading-[0.95] tracking-[-0.05em] md:text-7xl">
              Copilot ECG seguro para equipos clínicos.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#46534f]">
              Sube ECG, valida calidad, genera ayuda interpretativa, exporta
              informe, deja trazabilidad. Diseñado para médicos. No sustituye
              criterio clínico.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/sign-up"
                className="rounded-full bg-[#17211f] px-6 py-3 font-semibold text-[#f4f0e8] shadow-xl shadow-[#17211f]/10"
              >
                Empezar trial 7 días
              </Link>
              <Link
                href="/copilot"
                className="rounded-full border border-[#17211f]/20 px-6 py-3 font-semibold hover:bg-white/50"
              >
                Ver copilot
              </Link>
            </div>
          </div>
          <div className="relative rounded-[2rem] border border-[#17211f]/10 bg-[#17211f] p-5 text-[#f4f0e8] shadow-2xl">
            <div className="rounded-[1.5rem] bg-[#21312d] p-5">
              <div className="flex items-center justify-between border-b border-white/10 pb-4 text-sm">
                <span>ECG case · QRS-2049</span>
                <span className="rounded-full bg-[#d7ff63] px-2 py-1 text-[#17211f]">review needed</span>
              </div>
              <div className="mt-6 h-40 rounded-xl bg-[repeating-linear-gradient(0deg,rgba(215,255,99,.14)_0_1px,transparent_1px_16px),repeating-linear-gradient(90deg,rgba(215,255,99,.14)_0_1px,transparent_1px_16px)]" />
              <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                {["Quality 92%", "NORM 0.98", "CD 0.89"].map((item) => (
                  <div key={item} className="rounded-xl bg-white/8 p-3">{item}</div>
                ))}
              </div>
              <ol className="mt-5 space-y-2 text-sm text-white/75">
                {workflows.map((step, index) => (
                  <li key={step} className="flex gap-3">
                    <span className="text-[#d7ff63]">0{index + 1}</span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-20 md:grid-cols-4">
          {assurances.map((item) => (
            <div key={item} className="rounded-3xl border border-[#17211f]/10 bg-white/55 p-5 shadow-sm">
              <p className="text-sm font-semibold leading-6">{item}</p>
            </div>
          ))}
        </section>

        <section className="bg-[#17211f] px-5 py-16 text-[#f4f0e8]">
          <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-3">
            <div>
              <p className="text-sm uppercase tracking-[0.25em] text-[#d7ff63]">Enterprise ready</p>
              <h2 className="mt-3 text-4xl font-black tracking-tight">Seguridad antes que crecimiento.</h2>
            </div>
            <div className="rounded-3xl bg-white/8 p-6">
              <h3 className="font-bold">Cyber + compliance</h3>
              <p className="mt-3 text-sm leading-6 text-white/70">
                RLS por organización, JWT Clerk, audit chain, private storage,
                rate limits, no secretos en cliente, data retention.
              </p>
            </div>
            <div className="rounded-3xl bg-white/8 p-6">
              <h3 className="font-bold">Workflow médico</h3>
              <p className="mt-3 text-sm leading-6 text-white/70">
                Orquestación tipo Temporal: activities idempotentes para pago,
                análisis, reportes; workflows deterministas para estados.
              </p>
            </div>
          </div>
        </section>
      </main>
      <footer className="border-t border-[#17211f]/10 px-5 py-8 text-sm text-[#46534f]">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-3">
          <span>Axis · medical AI copilot beta</span>
          <span>Uso clínico requiere validación, contrato, DPA, revisión regulatoria.</span>
        </div>
      </footer>
    </div>
  );
}
