import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://heartscan.app";
const DESCRIPTION =
  "Clinical ECG copilot for care teams: upload an ECG, gate quality, get " +
  "calibrated interpretive support, export a report, keep an audit trail. " +
  "Decision support with human review — not an autonomous diagnosis.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Axis — Clinical ECG Copilot",
    template: "%s · Axis",
  },
  description: DESCRIPTION,
  applicationName: "Axis",
  keywords: [
    "ECG",
    "electrocardiogram",
    "clinical decision support",
    "cardiology copilot",
    "12-lead ECG analysis",
    "ECG triage",
    "medical AI",
  ],
  authors: [{ name: "Axis" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "Axis",
    title: "Axis — Clinical ECG Copilot",
    description: DESCRIPTION,
    url: SITE_URL,
    locale: "es_ES",
  },
  twitter: {
    card: "summary_large_image",
    title: "Axis — Clinical ECG Copilot",
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
};

export const viewport: Viewport = {
  themeColor: "#1b5fd9",
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="es"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-zinc-50 text-zinc-900">{children}</body>
      </html>
    </ClerkProvider>
  );
}
