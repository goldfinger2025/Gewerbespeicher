"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Battery,
  Sun,
  TrendingUp,
  ArrowRight,
  CheckCircle,
  Shield,
  Zap,
  FileText,
  Users,
  BarChart3,
  Loader2,
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // Check if user is already logged in - redirect to dashboard
  useEffect(() => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        router.push("/dashboard");
      } else {
        setIsCheckingAuth(false);
      }
    }
  }, [router]);

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Wird geladen...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Battery className="w-8 h-8 text-emerald-400" />
            <span className="text-xl font-bold text-white">
              Gewerbespeicher Planner
            </span>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              href="/auth/login"
              className="text-slate-300 hover:text-white transition"
            >
              Anmelden
            </Link>
            <Link
              href="/auth/register"
              className="btn-primary"
            >
              Kostenlos starten
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            Gewerbespeicher
            <br />
            <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
              intelligent planen
            </span>
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-8">
            KI-gestützte Planung und Angebotserstellung für PV-Speichersysteme.
            Simulieren Sie Ertrag, ROI und Autarkiegrad in Echtzeit.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/auth/register"
              className="btn-primary text-lg px-8 py-3 flex items-center justify-center gap-2"
            >
              Jetzt kostenlos starten
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/auth/login"
              className="text-slate-300 hover:text-white border border-slate-600 hover:border-slate-500 px-8 py-3 rounded-lg transition flex items-center justify-center gap-2"
            >
              Ich habe bereits ein Konto
            </Link>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <div className="card-hover bg-slate-800/50 border-slate-700">
            <Sun className="w-10 h-10 text-amber-400 mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              PV-Simulation
            </h3>
            <p className="text-slate-400">
              Präzise Ertragsberechnung mit pvlib und realen Wetterdaten
            </p>
          </div>

          <div className="card-hover bg-slate-800/50 border-slate-700">
            <Battery className="w-10 h-10 text-emerald-400 mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              Speicher-Logik
            </h3>
            <p className="text-slate-400">
              Intelligente Steuerung für maximale Eigenverbrauchsquote
            </p>
          </div>

          <div className="card-hover bg-slate-800/50 border-slate-700">
            <TrendingUp className="w-10 h-10 text-blue-400 mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              Wirtschaftlichkeit
            </h3>
            <p className="text-slate-400">
              ROI, Amortisation und jährliche Einsparungen auf einen Blick
            </p>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="bg-slate-800/30 py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Warum Gewerbespeicher Planner?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                  <Zap className="w-6 h-6 text-emerald-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Schnelle Projektanlage
                </h3>
                <p className="text-slate-400">
                  Erfassen Sie Kundenprojekte in wenigen Minuten und starten Sie sofort die Simulation.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-blue-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Detaillierte Analysen
                </h3>
                <p className="text-slate-400">
                  Eigenverbrauch, Autarkie, ROI und Amortisation auf einen Blick visualisiert.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-purple-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Professionelle Angebote
                </h3>
                <p className="text-slate-400">
                  Generieren Sie PDF-Angebote mit allen Simulationsergebnissen automatisch.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-amber-500/20 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-amber-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Kundenverwaltung
                </h3>
                <p className="text-slate-400">
                  Behalten Sie alle Ihre Projekte und Kunden übersichtlich im Blick.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-rose-500/20 rounded-lg flex items-center justify-center">
                  <Shield className="w-6 h-6 text-rose-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Sichere Daten
                </h3>
                <p className="text-slate-400">
                  Ihre Projekt- und Kundendaten werden sicher und DSGVO-konform gespeichert.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-cyan-500/20 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-cyan-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Einfache Bedienung
                </h3>
                <p className="text-slate-400">
                  Intuitive Oberfläche, die keine Schulung erfordert. Sofort loslegen.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Bereit, Ihre PV-Projekte effizienter zu planen?
          </h2>
          <p className="text-xl text-slate-300 mb-8">
            Starten Sie noch heute kostenlos und erstellen Sie Ihr erstes Projekt in wenigen Minuten.
          </p>
          <Link
            href="/auth/register"
            className="btn-primary text-lg px-10 py-4 inline-flex items-center gap-2"
          >
            Kostenlos registrieren
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-slate-500 text-sm mt-4">
            Keine Kreditkarte erforderlich • Sofortiger Zugang
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-700/50 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-400 text-sm">
          © 2025 EWS GmbH • Gewerbespeicher Planner v0.1.0
        </div>
      </footer>
    </main>
  );
}
