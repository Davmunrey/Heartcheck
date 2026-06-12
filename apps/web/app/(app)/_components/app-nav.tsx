"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Panel" },
  { href: "/analyze", label: "Analizar" },
  { href: "/settings/billing", label: "Billing" },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-5 text-sm">
      {links.map((l) => {
        const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`border-b-2 pb-0.5 font-medium transition-colors ${
              active
                ? "border-signal text-ink"
                : "border-transparent text-ink-2 hover:text-ink"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
