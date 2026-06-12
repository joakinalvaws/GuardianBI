import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Dashboard Guardian",
  description:
    "Agente IA que audita dashboards de Power BI: datos desactualizados, métricas inconsistentes y conflictos entre reportes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col font-sans">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-4xl items-baseline gap-3 px-6 py-4">
            <Link href="/" className="text-lg font-bold tracking-tight">
              🛡️ Dashboard Guardian
            </Link>
            <span className="hidden text-sm text-gray-500 sm:inline">
              Auditoría de dashboards con IA
            </span>
          </div>
        </header>

        <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-8">
          {children}
        </main>

        <footer className="border-t border-gray-200 bg-white py-4 text-center text-xs text-gray-400">
          Dashboard Guardian — agente auditor con GPT + Supabase
        </footer>
      </body>
    </html>
  );
}
