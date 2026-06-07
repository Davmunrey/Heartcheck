const lanes = [
  ["Upload", "JPEG/PNG/WebP ECG, API o consola"],
  ["Quality gate", "rotación, grid, trazado, ruido, derivaciones"],
  ["AI assist", "probabilidades NORM/MI/STTC/CD/HYP + heurísticas"],
  ["Doctor review", "validación humana, notas, override"],
  ["Report", "PDF/API, disclaimers, request id"],
  ["Learning", "feedback seguro → cola entrenamiento"],
];

export default function CopilotPage() {
  return (
    <section className="bg-scope px-5 py-20 text-scope-ink">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-brand-bright">ECG Copilot</p>
        <h1 className="mt-3 max-w-4xl text-5xl font-black tracking-[-0.04em] text-white">
          Ayuda clínica trazable, no caja negra autónoma.
        </h1>
        <p className="mt-5 max-w-2xl leading-7 text-scope-ink/70">
          Axis prepara casos, reduce fricción, genera evidencia operativa.
          El médico conserva la decisión final. Cada paso queda auditable.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {lanes.map(([title, body], idx) => (
            <section key={title} className="border-2 border-white/10 bg-white/5 p-6">
              <span className="font-mono text-brand-bright">0{idx + 1}</span>
              <h2 className="mt-4 text-xl font-bold text-white">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-scope-ink/65">{body}</p>
            </section>
          ))}
        </div>
      </div>
    </section>
  );
}
