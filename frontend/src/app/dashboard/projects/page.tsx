"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Battery,
  Sun,
  Plus,
  Search,
  Filter,
  MoreVertical,
  Trash2,
  Edit,
  Eye,
  ArrowRight,
  MapPin,
  Zap,
  Calendar,
} from "lucide-react";
import api from "@/lib/api-client";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  });

  const deleteProject = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setOpenMenu(null);
    },
  });

  // Filter projects
  const filteredProjects = projects?.items?.filter((project: any) => {
    const matchesSearch =
      !searchQuery ||
      project.customer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.project_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.city?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = !statusFilter || project.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const statusColors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-700",
    active: "bg-blue-100 text-blue-700",
    completed: "bg-emerald-100 text-emerald-700",
  };

  const statusLabels: Record<string, string> = {
    draft: "Entwurf",
    active: "Aktiv",
    completed: "Abgeschlossen",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projekte</h1>
          <p className="text-slate-500">
            {projects?.items?.length || 0} Projekte insgesamt
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

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Projekte durchsuchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-10"
            />
          </div>

          {/* Status Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setStatusFilter(null)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                !statusFilter
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              Alle
            </button>
            <button
              onClick={() => setStatusFilter("active")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                statusFilter === "active"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              Aktiv
            </button>
            <button
              onClick={() => setStatusFilter("completed")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                statusFilter === "completed"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              Abgeschlossen
            </button>
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="skeleton h-64 rounded-xl" />
          ))}
        </div>
      ) : filteredProjects?.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project: any) => (
            <div
              key={project.id}
              className="card hover:shadow-lg transition group relative"
            >
              {/* Menu Button */}
              <div className="absolute top-4 right-4">
                <button
                  onClick={() =>
                    setOpenMenu(openMenu === project.id ? null : project.id)
                  }
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <MoreVertical className="w-5 h-5" />
                </button>

                {/* Dropdown Menu */}
                {openMenu === project.id && (
                  <div className="absolute right-0 top-8 bg-white rounded-lg shadow-lg border border-slate-200 py-2 w-40 z-10">
                    <Link
                      href={`/dashboard/planner/${project.id}`}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      <Eye className="w-4 h-4" />
                      Ansehen
                    </Link>
                    <Link
                      href={`/dashboard/planner/${project.id}`}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      <Edit className="w-4 h-4" />
                      Bearbeiten
                    </Link>
                    <button
                      onClick={() => {
                        if (confirm("Projekt wirklich löschen?")) {
                          deleteProject.mutate(project.id);
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                    >
                      <Trash2 className="w-4 h-4" />
                      Löschen
                    </button>
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="mb-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`
                    w-12 h-12 rounded-lg flex items-center justify-center
                    ${
                      project.status === "completed"
                        ? "bg-emerald-100 text-emerald-600"
                        : project.status === "active"
                        ? "bg-blue-100 text-blue-600"
                        : "bg-slate-100 text-slate-600"
                    }
                  `}
                  >
                    <Battery className="w-6 h-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900 truncate">
                      {project.project_name || project.customer_name}
                    </h3>
                    <p className="text-sm text-slate-500 truncate">
                      {project.customer_company || project.customer_name}
                    </p>
                  </div>
                </div>
              </div>

              {/* Location */}
              {(project.city || project.postal_code) && (
                <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
                  <MapPin className="w-4 h-4" />
                  <span>
                    {project.city || project.postal_code}
                  </span>
                </div>
              )}

              {/* System Specs */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-amber-50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-amber-600 mb-1">
                    <Sun className="w-4 h-4" />
                    <span className="text-xs">PV-Leistung</span>
                  </div>
                  <p className="font-semibold text-amber-700">
                    {project.pv_peak_power_kw} kWp
                  </p>
                </div>
                <div className="bg-emerald-50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-emerald-600 mb-1">
                    <Battery className="w-4 h-4" />
                    <span className="text-xs">Speicher</span>
                  </div>
                  <p className="font-semibold text-emerald-700">
                    {project.battery_capacity_kwh} kWh
                  </p>
                </div>
              </div>

              {/* Consumption */}
              <div className="flex items-center justify-between text-sm text-slate-500 mb-4">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  <span>Verbrauch</span>
                </div>
                <span className="font-medium">
                  {project.annual_consumption_kwh?.toLocaleString("de-DE")} kWh/a
                </span>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    statusColors[project.status] || statusColors.draft
                  }`}
                >
                  {statusLabels[project.status] || "Entwurf"}
                </span>
                <Link
                  href={`/dashboard/planner/${project.id}`}
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm flex items-center gap-1"
                >
                  Öffnen
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Battery className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900 mb-2">
            {searchQuery || statusFilter
              ? "Keine Projekte gefunden"
              : "Noch keine Projekte"}
          </h3>
          <p className="text-slate-500 mb-6">
            {searchQuery || statusFilter
              ? "Versuchen Sie andere Suchbegriffe oder Filter"
              : "Erstellen Sie Ihr erstes PV-Speicher-Projekt"}
          </p>
          {!searchQuery && !statusFilter && (
            <Link
              href="/dashboard/planner"
              className="btn-primary inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Projekt erstellen
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
