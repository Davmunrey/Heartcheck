/**
 * Three distinct product illustrations for the landing pillars. Each one
 * *shows* a different part of the product so the three sections never look
 * alike. Pure SVG/HTML + brand tokens, no JS, no deps.
 */

const tone = { ok: "bg-ok", warn: "bg-warn", crit: "bg-signal" } as const;

/** Pillar 1 — "Informe completo": a real findings panel, not a waveform. */
export function FindingsVisual() {
  const rows: [string, keyof typeof tone, string][] = [
    ["Fibrilación auricular", "crit", "92%"],
    ["Bloqueo de rama der.", "warn", "58%"],
    ["Cambios ST/T", "warn", "41%"],
    ["Ritmo sinusal", "ok", "12%"],
  ];
  return (
    <div className="overflow-hidden border-2 border-line bg-surface shadow-2xl shadow-ink/5">
      <div className="flex items-center justify-between border-b-2 border-line bg-paper-2 px-5 py-3">
        <span className="font-mono text-xs font-semibold tracking-wide text-ink">INFORME · 27 afecciones</span>
        <span className="size-2 rounded-full bg-ok" />
      </div>
      <ul className="divide-y divide-line">
        {rows.map(([name, t, p]) => (
          <li key={name} className="flex items-center gap-3 px-5 py-3.5">
            <span className={`size-2.5 shrink-0 ${tone[t]}`} />
            <span className="flex-1 truncate text-sm font-medium text-ink">{name}</span>
            <div className="h-1.5 w-16 shrink-0 overflow-hidden bg-paper-2">
              <div className={`h-full ${tone[t]}`} style={{ width: p }} />
            </div>
            <span className="w-9 shrink-0 text-right font-mono text-xs text-ink-3">{p}</span>
          </li>
        ))}
      </ul>
      <div className="border-t-2 border-line bg-brand px-5 py-2.5 text-xs font-semibold text-white">
        + 23 afecciones más, priorizadas
      </div>
    </div>
  );
}

/** Pillar 2 — "Decides tú": confidence ring + bars + the human-review row. */
export function ConfidenceVisual() {
  const r = 26;
  const c = 2 * Math.PI * r;
  const pct = 0.92;
  const bars: [string, number, string][] = [
    ["Alta confianza", 92, "bg-ok"],
    ["A revisar", 58, "bg-warn"],
    ["Descartado", 14, "bg-ink-3"],
  ];
  return (
    <div className="border-2 border-line bg-surface p-6 shadow-2xl shadow-ink/5">
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 64 64" className="size-16 -rotate-90">
          <circle cx="32" cy="32" r={r} fill="none" stroke="var(--line)" strokeWidth="7" />
          <circle
            cx="32" cy="32" r={r} fill="none" stroke="var(--ok)" strokeWidth="7" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
          />
        </svg>
        <div>
          <p className="font-mono text-xs uppercase tracking-wide text-ink-3">Confianza</p>
          <p className="text-3xl font-black leading-none text-ink">92%</p>
        </div>
      </div>
      <div className="mt-6 space-y-3">
        {bars.map(([label, w, color]) => (
          <div key={label} className="flex items-center gap-3">
            <span className="w-28 shrink-0 text-xs font-medium text-ink-2">{label}</span>
            <div className="h-2 flex-1 overflow-hidden bg-paper-2">
              <div className={`h-full ${color}`} style={{ width: `${w}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-6 flex items-center gap-2.5 border-2 border-brand bg-brand-tint px-4 py-3">
        <span className="grid size-5 shrink-0 place-items-center bg-brand text-xs font-bold text-white">✓</span>
        <span className="text-sm font-semibold text-brand">Revisión médica · el doctor decide</span>
      </div>
    </div>
  );
}

/** Pillar 3 — "Listo para tu clínica": isolated tenants + roles + web/API. */
export function ClinicVisual() {
  const orgs: [string, string][] = [
    ["HN", "Hospital Norte"],
    ["CV", "Clínica Vega"],
  ];
  return (
    <div className="border-2 border-line bg-surface p-6 shadow-2xl shadow-ink/5">
      <div className="space-y-3">
        {orgs.map(([initials, name]) => (
          <div key={name} className="flex items-center gap-3 border-2 border-line bg-paper px-4 py-3">
            <span className="grid size-8 shrink-0 place-items-center bg-scope font-mono text-[10px] font-bold text-white">{initials}</span>
            <span className="flex-1 text-sm font-semibold text-ink">{name}</span>
            <svg viewBox="0 0 24 24" className="size-4 text-ink-3" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="5" y="11" width="14" height="9" rx="1" />
              <path d="M8 11V8a4 4 0 0 1 8 0v3" />
            </svg>
          </div>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {["Admin", "Médico", "Solo lectura"].map((role) => (
          <span key={role} className="bg-brand-tint px-2.5 py-1 font-mono text-xs text-brand">{role}</span>
        ))}
      </div>
      <div className="mt-5 flex items-center justify-between border-t-2 border-line pt-4">
        <span className="text-xs text-ink-3">Cada equipo, aislado</span>
        <span className="flex gap-1.5">
          <span className="bg-ink px-2 py-1 font-mono text-[10px] font-semibold text-white">WEB</span>
          <span className="bg-brand px-2 py-1 font-mono text-[10px] font-semibold text-white">API</span>
        </span>
      </div>
    </div>
  );
}

export const pillarVisuals = [FindingsVisual, ConfidenceVisual, ClinicVisual];
