import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata, Viewport } from "next";
import { Archivo, Archivo_Black, Geist_Mono, Hanken_Grotesk } from "next/font/google";
import "./globals.css";

// Axis brand type: Hanken Grotesk (body), Archivo (subheads), Archivo Black
// (display headings), Geist Mono (rubrics / numerals).
const fontSans = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const fontHead = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["600", "700", "800", "900"],
});

const fontDisplay = Archivo_Black({
  variable: "--font-archivo-black",
  subsets: ["latin"],
  weight: "400",
});

const fontMono = Geist_Mono({
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
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#1b5fd9",
          colorText: "#0b1a2b",
          colorBackground: "#ffffff",
          borderRadius: "0",
          fontFamily: 'var(--font-sans), "Hanken Grotesk", system-ui, sans-serif',
        },
      }}
    >
      <html
        lang="es"
        className={`${fontSans.variable} ${fontHead.variable} ${fontDisplay.variable} ${fontMono.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-paper text-ink">{children}</body>
      </html>
    </ClerkProvider>
  );
}
