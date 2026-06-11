import { Reveal } from "../_components/reveal";

const lanes = [
  ["Upload", "JPEG/PNG/WebP ECG, API o consola"],
  ["Quality gate", "rotación, grid, trazado, ruido, derivaciones"],
  ["AI assist", "probabilidades de 27 afecciones + heurísticas"],
  ["Doctor review", "validación humana, notas, override"],
  ["Report", "PDF/API, disclaimers, request id"],
  ["Learning", "feedback seguro → cola entrenamiento"],
];

export default function CopilotPage() {
  return (
    <section className="relative overflow-hidden bg-scope px-5 py-24 text-scope-ink md:py-32">
      <div className="orb-a pointer-events-none absolute -left-20 top-10 h-72 w-72 rounded-full bg-brand/20 blur-[100px]" />
      <div className="orb-b pointer-events-none absolute -right-16 bottom-10 h-64 w-64 rounded-full bg-signal/15 blur-[100px]" />
      <div className="relative mx-auto max-w-6xl">
        <Reveal variant="stagger">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">ECG Copilot</p>
          <h1 className="mt-4 max-w-4xl text-[clamp(2.4rem,5.5vw,4.5rem)] font-black leading-[0.98] tracking-[-0.045em] text-white">
            Ayuda clínica trazable, no caja negra autónoma.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-scope-ink/70">
            Axis prepara casos, reduce fricción, genera evidencia operativa.
            El médico conserva la decisión final. Cada paso queda auditable.
          </p>
        </Reveal>
        <Reveal variant="stagger" as="div" className="mt-12 grid gap-4 md:grid-cols-3">
          {lanes.map(([title, body], idx) => (
            <div key={title} className="border-2 border-white/10 bg-white/5 p-6 transition-colors hover:border-brand-bright/40 hover:bg-white/[0.08]">
              <span className="font-mono text-brand-bright">0{idx + 1}</span>
              <h2 className="mt-4 text-xl font-bold text-white">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-scope-ink/65">{body}</p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
