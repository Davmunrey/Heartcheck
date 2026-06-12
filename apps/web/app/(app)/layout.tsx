import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

import { AxisMark } from "@/app/(public)/_components/site-header";
import { getT } from "@/lib/i18n";
import { AppNav } from "./_components/app-nav";
import { LocaleSwitcher } from "./_components/locale-switcher";

export default async function AppShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { locale, t } = await getT();
  return (
    <div className="flex min-h-dvh flex-col bg-paper text-ink">
      <header className="border-b-2 border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-2.5 text-ink">
              <AxisMark className="size-8" />
              <span className="font-display text-lg tracking-[-0.04em]">Axis</span>
            </Link>
            <AppNav labels={t.nav} />
          </div>
          <div className="flex items-center gap-3">
            <LocaleSwitcher locale={locale} />
            <UserButton />
          </div>
        </div>
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}
