import Link from "next/link";

import { AxisMark } from "./site-header";

const footerLinks = [
  { href: "/copilot", label: "Copilot" },
  { href: "/pricing", label: "Planes" },
  { href: "/security", label: "Seguridad" },
  { href: "/enterprise", label: "Enterprise" },
  { href: "/faq", label: "FAQ" },
];

export function SiteFooter() {
  return (
    <footer className="border-t-2 border-ink/10 bg-paper px-5 py-10 text-sm">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2.5">
          <AxisMark className="size-7" />
          <span className="font-semibold text-ink">Axis</span>
          <span className="text-ink-3">· clinical ECG copilot</span>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2 text-ink-2">
          {footerLinks.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-brand">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
      <p className="mx-auto mt-6 max-w-7xl text-xs leading-5 text-ink-3">
        Axis es una herramienta de apoyo a la decisión clínica — probabilística, con revisión
        humana, <strong className="font-semibold text-ink-2">no diagnóstica</strong>. El uso clínico
        real requiere validación local, contrato, DPA/BAA y revisión regulatoria.
      </p>
    </footer>
  );
}
