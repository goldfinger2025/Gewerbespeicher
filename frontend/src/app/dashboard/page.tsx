"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Battery,
  Sun,
  TrendingUp,
  FileText,
  Plus,
  ArrowRight,
  Clock,
  CheckCircle,
  Calculator,
} from "lucide-react";
import api from "@/lib/api-client";

// Type definitions for API responses
interface Project {
  id: string;
  customer_name: string;
  project_name?: string;
  city?: string;
  postal_code?: string;
  pv_peak_power_kw: number;
  battery_capacity_kwh: number;
  status: "draft" | "active" | "completed" | "archived";
}

interface Offer {
  id: string;
  offer_number: string;
  status: "draft" | "sent" | "viewed" | "signed" | "completed" | "rejected";
}

interface ProjectsResponse {
  total: number;
  items: Project[];
}

interface OffersResponse {
  total: number;
  items: Offer[];
}

export default function DashboardPage() {
  const { data: projects, isLoading } = useQuery<ProjectsResponse>({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  });

  const { data: offers } = useQuery<OffersResponse>({
    queryKey: ["offers"],
    queryFn: () => api.getOffers(),
  });

  // Calculate stats with proper typing
  const projectItems = projects?.items ?? [];
  const offerItems = offers?.items ?? [];

  const totalProjects = projectItems.length;
  const activeProjects = projectItems.filter((p) => p.status === "active").length;
  const completedProjects = projectItems.filter((p) => p.status === "completed").length;
  const pendingOffers = offerItems.filter((o) =>
    o.status === "draft" || o.status === "sent" || o.status === "viewed"
  ).length;

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Willkommen zurück! 👋
          </h1>
          <p className="text-slate-500 mt-1">
            Hier ist eine Übersicht Ihrer Projekte
          </p>
        </div>
        <Link
          href="/dashboard/planner"
          className="btn-primary inline-flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Neues Projekt
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Gesamt Projekte</p>
              <p className="text-3xl font-bold mt-1">{totalProjects}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <Battery className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-emerald-100 text-sm">Aktive Projekte</p>
              <p className="text-3xl font-bold mt-1">{activeProjects}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <Clock className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-100 text-sm">Abgeschlossen</p>
              <p className="text-3xl font-bold mt-1">{completedProjects}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <CheckCircle className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="card bg-gradient-to-br from-purple-500 to-purple-600 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Offene Angebote</p>
              <p className="text-3xl font-bold mt-1">{pendingOffers}</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <FileText className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">Aktuelle Projekte</h2>
          <Link
            href="/dashboard/projects"
            className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
          >
            Alle anzeigen
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-20 rounded-lg" />
            ))}
          </div>
        ) : projectItems.length > 0 ? (
          <div className="space-y-4">
            {projectItems.slice(0, 5).map((project) => (
              <div
                key={project.id}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition"
              >
                <div className="flex items-center gap-4">
                  <div className={`
                    w-12 h-12 rounded-lg flex items-center justify-center
                    ${project.status === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                      project.status === 'active' ? 'bg-blue-100 text-blue-600' :
                      'bg-slate-200 text-slate-600'}
                  `}>
                    <Battery className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      {project.project_name || project.customer_name}
                    </h3>
                    <p className="text-sm text-slate-500">
                      {project.customer_name} • {project.city || project.postal_code}
                    </p>
                    <div className="flex gap-4 mt-1 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Sun className="w-3 h-3" />
                        {project.pv_peak_power_kw} kWp
                      </span>
                      <span className="flex items-center gap-1">
                        <Battery className="w-3 h-3" />
                        {project.battery_capacity_kwh} kWh
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`
                    px-3 py-1 rounded-full text-xs font-medium
                    ${project.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                      project.status === 'active' ? 'bg-blue-100 text-blue-700' :
                      'bg-slate-200 text-slate-600'}
                  `}>
                    {project.status === 'completed' ? 'Abgeschlossen' :
                     project.status === 'active' ? 'Aktiv' : 'Entwurf'}
                  </span>
                  <Link
                    href={`/dashboard/planner/${project.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Battery className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">
              Noch keine Projekte
            </h3>
            <p className="text-slate-500 mb-6">
              Erstellen Sie Ihr erstes PV-Speicher-Projekt
            </p>
            <Link href="/dashboard/planner" className="btn-primary">
              <Plus className="w-5 h-5 mr-2" />
              Projekt erstellen
            </Link>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-6">
        <Link
          href="/dashboard/planner"
          className="card hover:shadow-lg transition group"
        >
          <div className="flex items-center gap-4">
            <div className="bg-blue-100 p-3 rounded-lg group-hover:bg-blue-200 transition">
              <Calculator className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Neue Simulation</h3>
              <p className="text-sm text-slate-500">
                PV-Speicher dimensionieren
              </p>
            </div>
          </div>
        </Link>

        <Link
          href="/dashboard/offers"
          className="card hover:shadow-lg transition group"
        >
          <div className="flex items-center gap-4">
            <div className="bg-emerald-100 p-3 rounded-lg group-hover:bg-emerald-200 transition">
              <FileText className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Angebote</h3>
              <p className="text-sm text-slate-500">
                Angebote verwalten
              </p>
            </div>
          </div>
        </Link>

        <Link
          href="/dashboard/analytics"
          className="card hover:shadow-lg transition group"
        >
          <div className="flex items-center gap-4">
            <div className="bg-purple-100 p-3 rounded-lg group-hover:bg-purple-200 transition">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">Analytics</h3>
              <p className="text-sm text-slate-500">
                Statistiken & Reports
              </p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
