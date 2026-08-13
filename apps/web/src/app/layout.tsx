import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { RootProviders } from "@/components/providers/root-providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap"
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap"
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.PUBLIC_WEB_URL ?? "http://localhost:3000"),
  title: {
    default: "InsightForge AI — Business analytics that explains itself",
    template: "%s | InsightForge AI"
  },
  description:
    "Monitor performance, uncover trends, and turn business analytics into clear decisions with AI-guided insight.",
  applicationName: "InsightForge AI",
  keywords: [
    "business analytics",
    "SaaS dashboard",
    "AI insights",
    "revenue analytics"
  ],
  openGraph: {
    title: "InsightForge AI",
    description: "Turn business data into decisions.",
    type: "website",
    locale: "en_US"
  },
  robots: {
    index: true,
    follow: true
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#07111f"
};

export default function RootLayout({
  children
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="font-sans antialiased">
        <a
          href="#main-content"
          className="text-ink-950 fixed top-3 left-3 z-[200] -translate-y-20 rounded-lg bg-white px-4 py-2 text-sm font-semibold shadow-lg transition-transform focus:translate-y-0"
        >
          Skip to main content
        </a>
        <RootProviders>{children}</RootProviders>
      </body>
    </html>
  );
}
