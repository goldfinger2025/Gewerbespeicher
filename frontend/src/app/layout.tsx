import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";

export const metadata: Metadata = {
  title: "Gewerbespeicher Planner",
  description: "KI-gestützte Planung von PV-Speichersystemen für Gewerbe",
  keywords: ["PV", "Photovoltaik", "Speicher", "Gewerbe", "Solar", "EWS"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className="font-sans bg-slate-50 antialiased">
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
