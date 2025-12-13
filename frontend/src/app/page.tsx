"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api-client";
import { ProjectForm } from "@/components/forms/ProjectForm";
import { 
  Battery, 
  Sun, 
  TrendingUp, 
  Plus, 
  ArrowRight,
  Building2
} from "lucide-react";

export default function HomePage() {
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  });

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
              href="/dashboard" 
              className="text-slate-300 hover:text-white transition"
            >
              Dashboard
            </Link>
            <Link 
              href="/auth/login" 
              className="btn-primary"
            >
              Anmelden
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            🔋 Gewerbespeicher
            <br />
            <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
              intelligent planen
            </span>
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto">
            KI-gestützte Planung und Angebotserstellung für PV-Speichersysteme. 
            Simulieren Sie Ertrag, ROI und Autarkiegrad in Echtzeit.
          </p>
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

      {/* Main Grid */}
      <section className="max-w-7xl mx-auto px-4 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Create Project */}
          <div className="lg:col-span-1">
            <div className="card">
              <div className="flex items-center gap-2 mb-6">
                <Plus className="w-5 h-5 text-blue-600" />
                <h2 className="text-xl font-bold">Neues Projekt</h2>
              </div>
              <ProjectForm
                onSubmit={async (data) => {
                  const result = await api.createProject(data);
                  window.location.href = `/dashboard/planner/${result.id}`;
                }}
              />
            </div>
          </div>

          {/* Active Projects */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-emerald-600" />
                  <h2 className="text-xl font-bold">Aktive Projekte</h2>
                </div>
                <span className="text-sm text-slate-500">
                  {projects?.length || 0} Projekte
                </span>
              </div>
              
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="skeleton h-20 rounded-lg" />
                  ))}
                </div>
              ) : projects && projects.length > 0 ? (
                <div className="space-y-4">
                  {projects.map((project: any) => (
                    <div
                      key={project.id}
                      className="p-4 border border-slate-200 rounded-lg hover:shadow-md hover:border-blue-200 transition group"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-bold text-lg group-hover:text-blue-600 transition">
                            {project.project_name || "Unbenanntes Projekt"}
                          </h3>
                          <p className="text-slate-600 text-sm">
                            {project.customer_name} • {project.city || project.postal_code}
                          </p>
                          <div className="flex gap-4 mt-2 text-sm text-slate-500">
                            <span>⚡ {project.pv_peak_power_kw} kWp</span>
                            <span>🔋 {project.battery_capacity_kwh} kWh</span>
                          </div>
                        </div>
                        <Link 
                          href={`/dashboard/planner/${project.id}`}
                          className="btn-primary flex items-center gap-1"
                        >
                          Bearbeiten
                          <ArrowRight className="w-4 h-4" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Battery className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500">
                    Noch keine Projekte erstellt.
                  </p>
                  <p className="text-sm text-slate-400 mt-1">
                    Erstellen Sie Ihr erstes Projekt links.
                  </p>
                </div>
              )}
            </div>
          </div>
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
