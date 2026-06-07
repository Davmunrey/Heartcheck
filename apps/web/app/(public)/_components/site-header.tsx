import Link from "next/link";

const navLinks = [
  { href: "/copilot", label: "Copilot" },
  { href: "/security", label: "Seguridad" },
  { href: "/pricing", label: "Planes" },
  { href: "/enterprise", label: "Enterprise" },
  { href: "/faq", label: "FAQ" },
];

/** Axis brandmark: red square (the ECG signal) + blue wordmark (the product). */
export function Brandmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight text-ink">
      <span className="grid size-9 place-items-center bg-signal font-mono text-sm font-bold text-white">
        ECG
      </span>
      <span className="text-lg">Axis</span>
      <span className="bg-brand-tint px-2 py-0.5 text-xs font-medium text-brand">
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
      </div>
    </header>
  );
}
