"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function AppNav({ labels }: { labels: { panel: string; analyze: string; billing: string } }) {
  const pathname = usePathname();
  const links = [
    { href: "/dashboard", label: labels.panel },
    { href: "/analyze", label: labels.analyze },
    { href: "/settings/billing", label: labels.billing },
  ];
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
