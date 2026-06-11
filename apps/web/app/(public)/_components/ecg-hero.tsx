/**
 * Dark ECG scope for the hero — the trace draws itself (stroke-dashoffset),
 * a soft blip sweeps across, grid + glow. Pure SVG/CSS, no JS, no deps.
 */
export function EcgHero() {
  // a believable lead-II rhythm: baseline, P, QRS spike, T wave, repeated.
  const beat = "l34 0 q6 0 9 -10 q3 -10 7 0 l5 0 l4 30 l5 -64 l5 46 l5 -12 q5 0 9 14 q3 10 7 0 l30 0";
  const path = `M0 130 ${beat} ${beat} ${beat} l40 0`;
  return (
    <div className="relative overflow-hidden bg-scope shadow-2xl">
      {/* grid */}
      <div className="absolute inset-0 opacity-[0.18] [background:repeating-linear-gradient(0deg,rgba(61,123,255,.5)_0_1px,transparent_1px_22px),repeating-linear-gradient(90deg,rgba(61,123,255,.5)_0_1px,transparent_1px_22px)]" />
      {/* glow */}
      <div className="orb-a absolute -left-10 top-1/2 h-40 w-40 -translate-y-1/2 rounded-full bg-brand/30 blur-3xl" />
      <div className="orb-b absolute right-0 top-6 h-32 w-32 rounded-full bg-signal/25 blur-3xl" />
      <div className="relative p-6 sm:p-8">
        <div className="flex items-center justify-between text-xs text-scope-ink/70">
          <span className="font-mono">LEAD II · 100 mm/s</span>
          <span className="flex items-center gap-2 font-mono">
            <span className="size-1.5 animate-pulse rounded-full bg-signal" /> LIVE
          </span>
        </div>
        <svg viewBox="0 0 640 200" className="mt-4 h-40 w-full sm:h-52" preserveAspectRatio="none">
          <path d={path} className="ecg-path" fill="none" stroke="var(--signal-bright)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          {/* sweeping highlight */}
          <rect className="ecg-blip" x="0" y="0" width="60" height="200" fill="url(#sweep)" />
          <defs>
            <linearGradient id="sweep" x1="0" x2="1">
              <stop offset="0" stopColor="rgba(255,59,67,0)" />
              <stop offset="1" stopColor="rgba(255,59,67,0.35)" />
            </linearGradient>
          </defs>
        </svg>
        <div className="mt-5 grid grid-cols-3 gap-3 font-mono text-[11px]">
          {[
            ["RITMO", "Sinusal 72 lpm"],
            ["HALLAZGOS", "2 a revisar"],
            ["LISTO EN", "~20 s"],
          ].map(([k, v]) => (
            <div key={k} className="border border-white/10 bg-white/5 p-3">
              <div className="text-scope-ink/50">{k}</div>
              <div className="mt-1 text-white">{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
