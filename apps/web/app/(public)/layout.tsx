import type { ReactNode } from "react";

import { SiteFooter } from "./_components/site-footer";
import { SiteHeader } from "./_components/site-header";

/**
 * Shared chrome for every marketing/public page so the Axis branding is
 * identical everywhere. Pages render only their content; the header, footer
 * and paper/ink surface come from here.
 */
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-paper text-ink">
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
