import type { Metadata, Viewport } from "next";
import { Suspense, type ReactNode } from "react";
import { Bricolage_Grotesque, IBM_Plex_Mono, IBM_Plex_Sans_Devanagari } from "next/font/google";
import { Footer } from "@/components/Footer";
import { RouteProgress } from "@/components/RouteProgress";
import "./globals.css";

// Self-host the three brand families with next/font (was three render-blocking <link>s to Google's CDN).
// Each exposes a CSS variable that globals.css + inline styles reference (--font-serif / -mono / -deva);
// `display: swap` keeps text visible while the font loads and next/font's size-adjust fallback avoids the
// layout shift the old <link> approach had. Bricolage is variable (opsz + wght axes); the IBM Plex faces
// are non-variable, so their weights must be listed explicitly.
const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  axes: ["opsz"],
  display: "swap",
  variable: "--font-serif",
});
const plexDeva = IBM_Plex_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-deva",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-mono",
});

// Canonical site URL for metadata / OG / canonical links. Defaults to the custom domain (NOT Vercel's
// *.vercel.app alias, which VERCEL_PROJECT_PRODUCTION_URL would give); override per-env if needed.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://neta-resume.app";

const DESCRIPTION =
  "Offices held, parties switched, wealth declared, and cases pending — every fact sourced to the " +
  "Election Commission and shown without spin. A free, open public record of every Indian legislator.";

// Explicit mobile viewport. width=device-width + initialScale 1 is Next's default, set here explicitly;
// deliberately NOT locking maximumScale/userScalable so pinch-zoom stays available (accessibility).
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Neta·Resume — the public record of every Indian legislator",
    template: "%s · Neta·Resume",
  },
  description: DESCRIPTION,
  applicationName: "Neta·Resume",
  keywords: [
    "Indian legislators", "Lok Sabha", "Rajya Sabha", "Member of Parliament", "ECI affidavit",
    "criminal cases", "declared assets", "party switches", "public record",
  ],
  openGraph: {
    type: "website",
    siteName: "Neta·Resume",
    url: siteUrl,
    title: "Neta·Resume — the public record of every Indian legislator",
    description:
      "Wealth declared, cases pending, parties switched, offices held — sourced to the Election " +
      "Commission, for every MP.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Neta·Resume — the public record of every Indian legislator",
    description: "The sourced public record of every Indian legislator — wealth, cases, parties, offices.",
  },
};

// Apply the saved theme before paint to avoid a flash of the wrong theme.
const themeInit = `(function(){try{var t=localStorage.getItem('nr-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${bricolage.variable} ${plexDeva.variable} ${plexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="scroll">
        <Suspense fallback={null}><RouteProgress /></Suspense>
        {children}
        <Footer />
      </body>
    </html>
  );
}
