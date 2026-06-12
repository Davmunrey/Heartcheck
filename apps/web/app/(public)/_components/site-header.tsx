import Link from "next/link";

const navLinks = [
  { href: "/copilot", label: "Copilot" },
  { href: "/security", label: "Seguridad" },
  { href: "/pricing", label: "Planes" },
  { href: "/enterprise", label: "Enterprise" },
  { href: "/faq", label: "FAQ" },
];

/**
 * Axis mark — the cardiac electrical *axis* (blue vector) with the patient's
 * ECG pulse (red) crossing it, on a dark scope tile with a faint grid. Ties
 * the brand name to its meaning. Pure SVG, scales crisply at any size.
 */
export function AxisMark({ className = "size-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" className={className} aria-hidden="true" role="img">
      <rect width="36" height="36" fill="var(--scope)" />
      <path d="M0 12h36M0 24h36M12 0v36M24 0v36" stroke="rgba(61,123,255,.20)" strokeWidth="1" />
      <path d="M6 30 30 9" stroke="var(--brand-bright)" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
      <path
        d="M3 21h7l2-5 3 11 3-16 3 12 2-2h6"
        fill="none" stroke="var(--signal-bright)" strokeWidth="2"
        strokeLinejoin="round" strokeLinecap="round"
      />
    </svg>
  );
}

/** Axis brandmark: the Axis mark + wordmark + positioning tag. */
export function Brandmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight text-ink">
      <AxisMark />
      <span className="font-display text-xl tracking-[-0.04em]">Axis</span>
      <span className="hidden bg-brand-tint px-2 py-0.5 text-xs font-medium text-brand sm:inline">
        clinical copilot
      </span>
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b-2 border-ink/10 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
        <Brandmark />
        <nav className="hidden items-center gap-6 text-sm font-medium md:flex">
          {navLinks.map((link) => (
            <Link key={link.href} href={link.href} className="text-ink-2 transition-colors hover:text-brand">
              {link.label}
            </Link>
          ))}
          <Link href="/sign-in" className="text-ink-2 transition-colors hover:text-brand">
            Entrar
          </Link>
          <Link
            href="/sign-up"
            className="bg-brand px-4 py-2 font-semibold text-white transition-colors hover:bg-brand-strong"
          >
            Trial 7 días
          </Link>
        </nav>

        {/* Mobile menu — no-JS <details> disclosure */}
        <details className="relative md:hidden">
          <summary
            aria-label="Abrir menú"
            className="grid size-9 cursor-pointer list-none place-items-center border-2 border-ink/15 text-ink [&::-webkit-details-marker]:hidden"
          >
            <span className="text-lg leading-none">≡</span>
          </summary>
          <div className="absolute right-0 top-full z-50 mt-2 flex w-52 flex-col gap-1 border-2 border-line bg-surface p-2 shadow-lg">
            {navLinks.map((link) => (
              <Link key={link.href} href={link.href} className="px-3 py-2 text-sm text-ink-2 hover:bg-paper-2 hover:text-brand">
                {link.label}
              </Link>
            ))}
            <Link href="/sign-in" className="px-3 py-2 text-sm text-ink-2 hover:bg-paper-2 hover:text-brand">
              Entrar
            </Link>
            <Link href="/sign-up" className="mt-1 bg-brand px-3 py-2 text-center text-sm font-semibold text-white hover:bg-brand-strong">
              Trial 7 días
            </Link>
          </div>
        </details>
      </div>
    </header>
  );
}
