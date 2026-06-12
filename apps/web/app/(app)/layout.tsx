import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

import { AxisMark } from "@/app/(public)/_components/site-header";

export default function AppShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-paper text-ink">
      <header className="border-b-2 border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-2.5 text-ink">
              <AxisMark className="size-8" />
              <span className="font-display text-lg tracking-[-0.04em]">Axis</span>
            </Link>
            <nav className="flex gap-4 text-sm text-ink-2">
              <Link href="/dashboard" className="hover:text-brand">
                Panel
              </Link>
              <Link href="/analyze" className="hover:text-brand">
                Analizar
              </Link>
              <Link href="/settings/billing" className="hover:text-brand">
                Billing
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <UserButton />
          </div>
        </div>
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}
