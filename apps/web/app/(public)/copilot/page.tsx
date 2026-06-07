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
    <main className="min-h-full bg-[#17211f] px-5 py-16 text-[#f4f0e8]">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm uppercase tracking-[0.25em] text-[#d7ff63]">ECG Copilot</p>
        <h1 className="mt-3 max-w-4xl text-5xl font-black tracking-[-0.04em]">
          Ayuda clínica trazable, no caja negra autónoma.
        </h1>
        <p className="mt-5 max-w-2xl leading-7 text-white/70">
          Axis prepara casos, reduce fricción, genera evidencia operativa.
          Médico conserva decisión final. Cada paso queda auditable.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {lanes.map(([title, body], idx) => (
            <section key={title} className="rounded-3xl border border-white/10 bg-white/8 p-6">
              <span className="text-[#d7ff63]">0{idx + 1}</span>
              <h2 className="mt-4 text-xl font-bold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-white/65">{body}</p>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}

