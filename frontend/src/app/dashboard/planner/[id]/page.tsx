"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Battery,
  Sun,
  Zap,
  ArrowLeft,
  Calculator,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
  ChevronRight,
  BarChart3,
  Workflow,
  Euro,
  X,
  CheckCircle,
  TrendingUp,
  Target,
  Wallet,
} from "lucide-react";
import api from "@/lib/api-client";
import { SimulationResults } from "@/components/visualizations/SimulationResults";
import { EnergyFlowDiagram } from "@/components/visualizations/EnergyFlowDiagram";
import { BatteryInsights } from "@/components/visualizations/BatteryInsights";
import { FinancialAnalysis } from "@/components/visualizations/FinancialAnalysis";
import { ProjectForm } from "@/components/forms/ProjectForm";

type ResultsView = "overview" | "energy-flow" | "battery" | "financial";

interface OptimizationResult {
  optimized_pv_kw: number;
  optimized_battery_kwh: number;
  optimized_battery_power_kw: number;
  expected_autonomy_percent: number;
  expected_savings_eur: number;
  expected_payback_years: number;
  investment_delta_eur: number;
  recommendations: string[];
  reasoning: string;
}

export default function PlannerPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const projectId = params?.id as string | undefined;

  const [activeTab, setActiveTab] = useState<"config" | "results" | "offer">("config");
  const [resultsView, setResultsView] = useState<ResultsView>("overview");
  const [isSimulating, setIsSimulating] = useState(false);
  const [showOptimizationModal, setShowOptimizationModal] = useState(false);
  const [optimizationTarget, setOptimizationTarget] = useState<"max-roi" | "max-autonomy" | "min-cost">("max-roi");
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);

  // Fetch project if editing
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  // Fetch simulation results
  const { data: simulation, refetch: refetchSimulation } = useQuery({
    queryKey: ["simulation", projectId],
    queryFn: () => api.simulate(projectId!),
    enabled: false, // Only run manually
  });

  // Create project mutation
  const createProject = useMutation({
    mutationFn: (data: any) => api.createProject(data),
    onSuccess: (result) => {
      router.push(`/dashboard/planner/${result.id}`);
    },
  });

  // Update project mutation
  const updateProject = useMutation({
    mutationFn: (data: any) => api.updateProject(projectId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  // Run simulation
  const runSimulation = async () => {
    if (!projectId) return;

    setIsSimulating(true);
    try {
      await refetchSimulation();
      setActiveTab("results");
    } finally {
      setIsSimulating(false);
    }
  };

  // Generate offer
  const generateOffer = useMutation({
    mutationFn: () => {
      if (!simulation?.id) {
        throw new Error("Keine Simulation vorhanden");
      }
      return api.createOffer(simulation.id);
    },
    onSuccess: (result) => {
      router.push(`/dashboard/offers/${result.id}`);
    },
    onError: (error: Error) => {
      console.error("Fehler beim Erstellen des Angebots:", error);
      alert(`Fehler beim Erstellen des Angebots: ${error.message}`);
    },
  });

  // KI-Optimization mutation
  const optimizeSystem = useMutation({
    mutationFn: async () => {
      return api.optimize(projectId!, { optimization_target: optimizationTarget });
    },
    onSuccess: (result) => {
      setOptimizationResult(result);
    },
  });

  // Apply optimization to project
  const applyOptimization = async () => {
    if (!optimizationResult || !projectId) return;

    await updateProject.mutateAsync({
      pv_peak_power_kw: optimizationResult.optimized_pv_kw,
      battery_capacity_kwh: optimizationResult.optimized_battery_kwh,
      battery_power_kw: optimizationResult.optimized_battery_power_kw,
    });

    setShowOptimizationModal(false);
    setOptimizationResult(null);
  };

  // Handle form submit
  const handleFormSubmit = async (data: any) => {
    if (projectId) {
      await updateProject.mutateAsync(data);
    } else {
      await createProject.mutateAsync(data);
    }
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // Results sub-navigation
  const resultsNavItems = [
    { id: "overview" as ResultsView, label: "Übersicht", icon: BarChart3 },
    { id: "energy-flow" as ResultsView, label: "Energiefluss", icon: Workflow },
    { id: "battery" as ResultsView, label: "Batterie", icon: Battery },
    { id: "financial" as ResultsView, label: "Wirtschaftlichkeit", icon: Euro },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-slate-400 hover:text-slate-600 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {project?.project_name || "Neues Projekt"}
            </h1>
            {project?.customer_name && (
              <p className="text-slate-500">
                {project.customer_name} • {project.city || project.postal_code}
              </p>
            )}
          </div>
        </div>

        {projectId && (
          <div className="flex items-center gap-3">
            <button
              onClick={runSimulation}
              disabled={isSimulating}
              className="btn-primary flex items-center gap-2"
            >
              {isSimulating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Simuliere...
                </>
              ) : (
                <>
                  <Calculator className="w-4 h-4" />
                  Simulation starten
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      {projectId && (
        <div className="border-b border-slate-200">
          <nav className="flex gap-8">
            <button
              onClick={() => setActiveTab("config")}
              className={`
                py-4 border-b-2 font-medium text-sm transition
                ${activeTab === "config"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"}
              `}
            >
              <span className="flex items-center gap-2">
                <Sun className="w-4 h-4" />
                Konfiguration
              </span>
            </button>
            <button
              onClick={() => setActiveTab("results")}
              disabled={!simulation}
              className={`
                py-4 border-b-2 font-medium text-sm transition
                ${activeTab === "results"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"}
                ${!simulation && "opacity-50 cursor-not-allowed"}
              `}
            >
              <span className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Ergebnisse
                {simulation && (
                  <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs">
                    4 Ansichten
                  </span>
                )}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("offer")}
              disabled={!simulation}
              className={`
                py-4 border-b-2 font-medium text-sm transition
                ${activeTab === "offer"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"}
                ${!simulation && "opacity-50 cursor-not-allowed"}
              `}
            >
              <span className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Angebot
              </span>
            </button>
          </nav>
        </div>
      )}

      {/* Tab Content */}
      <div className="animate-fade-in">
        {activeTab === "config" && (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Configuration Form */}
            <div className="lg:col-span-2">
              <div className="card">
                <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                  <Battery className="w-5 h-5 text-blue-600" />
                  Projektkonfiguration
                </h2>
                <ProjectForm
                  onSubmit={handleFormSubmit}
                  initialData={project}
                  isEditing={!!projectId}
                />
              </div>
            </div>

            {/* Quick Preview */}
            <div className="lg:col-span-1 space-y-6">
              {project && (
                <>
                  <div className="card">
                    <h3 className="font-semibold mb-4">Systemübersicht</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-500 flex items-center gap-2">
                          <Sun className="w-4 h-4 text-amber-500" />
                          PV-Leistung
                        </span>
                        <span className="font-semibold">
                          {project.pv_peak_power_kw} kWp
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-500 flex items-center gap-2">
                          <Battery className="w-4 h-4 text-emerald-500" />
                          Speicher
                        </span>
                        <span className="font-semibold">
                          {project.battery_capacity_kwh} kWh
                        </span>
                      </div>
                      <div className="flex items-center justify-between py-2">
                        <span className="text-slate-500 flex items-center gap-2">
                          <Zap className="w-4 h-4 text-blue-500" />
                          Verbrauch
                        </span>
                        <span className="font-semibold">
                          {project.annual_consumption_kwh?.toLocaleString("de-DE")} kWh/a
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* AI Optimization Teaser */}
                  <div className="card bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
                    <div className="flex items-start gap-3">
                      <div className="bg-purple-100 p-2 rounded-lg">
                        <Sparkles className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-purple-900">
                          KI-Optimierung
                        </h3>
                        <p className="text-sm text-purple-700 mt-1">
                          Lassen Sie Claude die optimale Systemgröße für Ihren
                          Anwendungsfall berechnen.
                        </p>
                        <button
                          onClick={() => setShowOptimizationModal(true)}
                          className="text-sm text-purple-600 font-medium mt-2 flex items-center gap-1 hover:text-purple-700"
                        >
                          System optimieren
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* KI Optimization Modal */}
        {showOptimizationModal && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-purple-100 p-2 rounded-lg">
                    <Sparkles className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">KI-Systemoptimierung</h2>
                    <p className="text-sm text-slate-500">Powered by Claude Opus 4.5</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowOptimizationModal(false);
                    setOptimizationResult(null);
                  }}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="p-6">
                {!optimizationResult ? (
                  <>
                    <p className="text-slate-600 mb-6">
                      Wählen Sie Ihr Optimierungsziel. Claude analysiert Ihre Projektdaten
                      und empfiehlt die optimale Systemkonfiguration.
                    </p>

                    {/* Optimization Target Selection */}
                    <div className="grid gap-4 mb-6">
                      <button
                        onClick={() => setOptimizationTarget("max-roi")}
                        className={`p-4 rounded-xl border-2 text-left transition ${
                          optimizationTarget === "max-roi"
                            ? "border-purple-500 bg-purple-50"
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${optimizationTarget === "max-roi" ? "bg-purple-100" : "bg-slate-100"}`}>
                            <TrendingUp className={`w-5 h-5 ${optimizationTarget === "max-roi" ? "text-purple-600" : "text-slate-500"}`} />
                          </div>
                          <div>
                            <h3 className="font-semibold text-slate-900">Maximaler ROI</h3>
                            <p className="text-sm text-slate-500">Schnellste Amortisation der Investition</p>
                          </div>
                        </div>
                      </button>

                      <button
                        onClick={() => setOptimizationTarget("max-autonomy")}
                        className={`p-4 rounded-xl border-2 text-left transition ${
                          optimizationTarget === "max-autonomy"
                            ? "border-purple-500 bg-purple-50"
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${optimizationTarget === "max-autonomy" ? "bg-purple-100" : "bg-slate-100"}`}>
                            <Target className={`w-5 h-5 ${optimizationTarget === "max-autonomy" ? "text-purple-600" : "text-slate-500"}`} />
                          </div>
                          <div>
                            <h3 className="font-semibold text-slate-900">Maximale Autarkie</h3>
                            <p className="text-sm text-slate-500">Höchste Unabhängigkeit vom Stromnetz</p>
                          </div>
                        </div>
                      </button>

                      <button
                        onClick={() => setOptimizationTarget("min-cost")}
                        className={`p-4 rounded-xl border-2 text-left transition ${
                          optimizationTarget === "min-cost"
                            ? "border-purple-500 bg-purple-50"
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${optimizationTarget === "min-cost" ? "bg-purple-100" : "bg-slate-100"}`}>
                            <Wallet className={`w-5 h-5 ${optimizationTarget === "min-cost" ? "text-purple-600" : "text-slate-500"}`} />
                          </div>
                          <div>
                            <h3 className="font-semibold text-slate-900">Minimale Kosten</h3>
                            <p className="text-sm text-slate-500">Niedrigste Investitionskosten</p>
                          </div>
                        </div>
                      </button>
                    </div>

                    <button
                      onClick={() => optimizeSystem.mutate()}
                      disabled={optimizeSystem.isPending}
                      className="btn-primary w-full py-3 flex items-center justify-center gap-2"
                    >
                      {optimizeSystem.isPending ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Claude analysiert...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5" />
                          Optimierung starten
                        </>
                      )}
                    </button>

                    {optimizeSystem.isError && (
                      <p className="mt-4 text-red-600 text-sm">
                        Fehler bei der Optimierung. Bitte versuchen Sie es erneut.
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    {/* Optimization Results */}
                    <div className="space-y-6">
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                        <div className="flex items-center gap-2 text-emerald-700 mb-2">
                          <CheckCircle className="w-5 h-5" />
                          <span className="font-semibold">Optimierung abgeschlossen</span>
                        </div>
                        <p className="text-sm text-emerald-600">{optimizationResult.reasoning}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-50 rounded-xl p-4">
                          <p className="text-sm text-slate-500">Optimierte PV-Leistung</p>
                          <p className="text-2xl font-bold text-amber-600">
                            {optimizationResult.optimized_pv_kw.toFixed(1)} kWp
                          </p>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-4">
                          <p className="text-sm text-slate-500">Optimierter Speicher</p>
                          <p className="text-2xl font-bold text-emerald-600">
                            {optimizationResult.optimized_battery_kwh.toFixed(1)} kWh
                          </p>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-4">
                          <p className="text-sm text-slate-500">Erwartete Autarkie</p>
                          <p className="text-2xl font-bold text-blue-600">
                            {optimizationResult.expected_autonomy_percent.toFixed(0)}%
                          </p>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-4">
                          <p className="text-sm text-slate-500">Jährliche Ersparnis</p>
                          <p className="text-2xl font-bold text-purple-600">
                            {optimizationResult.expected_savings_eur.toLocaleString('de-DE')} €
                          </p>
                        </div>
                      </div>

                      {optimizationResult.recommendations.length > 0 && (
                        <div className="border-t border-slate-200 pt-4">
                          <h4 className="font-semibold text-slate-900 mb-2">Empfehlungen</h4>
                          <ul className="space-y-2">
                            {optimizationResult.recommendations.map((rec, idx) => (
                              <li key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                                <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="flex gap-4 pt-4">
                        <button
                          onClick={() => setOptimizationResult(null)}
                          className="btn-secondary flex-1"
                        >
                          Andere Ziele prüfen
                        </button>
                        <button
                          onClick={applyOptimization}
                          disabled={updateProject.isPending}
                          className="btn-primary flex-1 flex items-center justify-center gap-2"
                        >
                          {updateProject.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <CheckCircle className="w-4 h-4" />
                          )}
                          Werte übernehmen
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "results" && simulation && (
          <div className="space-y-6">
            {/* Results Sub-Navigation */}
            <div className="flex flex-wrap gap-2 bg-slate-100 p-1 rounded-lg w-fit">
              {resultsNavItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setResultsView(item.id)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition
                    ${resultsView === item.id
                      ? "bg-white text-blue-600 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"}
                  `}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </button>
              ))}
            </div>

            {/* Results Content */}
            <div className="animate-fade-in">
              {resultsView === "overview" && (
                <SimulationResults
                  results={simulation.results}
                  projectName={project?.project_name}
                />
              )}

              {resultsView === "energy-flow" && (
                <div className="grid lg:grid-cols-2 gap-6">
                  <EnergyFlowDiagram
                    pvGeneration={simulation.results?.pv_generation_kwh || 0}
                    selfConsumption={simulation.results?.self_consumption_kwh || 0}
                    gridExport={simulation.results?.grid_export_kwh || 0}
                    gridImport={simulation.results?.grid_import_kwh || 0}
                    batteryCapacity={project?.battery_capacity_kwh || 0}
                  />
                  <div className="card">
                    <h3 className="text-lg font-semibold text-slate-800 mb-4">Energiebilanz</h3>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center py-3 border-b border-slate-100">
                        <span className="text-slate-600">PV-Erzeugung</span>
                        <span className="font-semibold text-amber-600">
                          {(simulation.results?.pv_generation_kwh || 0).toLocaleString('de-DE')} kWh/a
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-3 border-b border-slate-100">
                        <span className="text-slate-600">Eigenverbrauch</span>
                        <span className="font-semibold text-emerald-600">
                          {(simulation.results?.self_consumption_kwh || 0).toLocaleString('de-DE')} kWh/a
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-3 border-b border-slate-100">
                        <span className="text-slate-600">Netzeinspeisung</span>
                        <span className="font-semibold text-violet-600">
                          {(simulation.results?.grid_export_kwh || 0).toLocaleString('de-DE')} kWh/a
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-3">
                        <span className="text-slate-600">Netzbezug</span>
                        <span className="font-semibold text-blue-600">
                          {(simulation.results?.grid_import_kwh || 0).toLocaleString('de-DE')} kWh/a
                        </span>
                      </div>
                    </div>
                    <div className="mt-6 p-4 bg-emerald-50 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-emerald-800">Autarkiegrad</span>
                        <span className="text-2xl font-bold text-emerald-600">
                          {(simulation.results?.autonomy_degree_percent || 0).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {resultsView === "battery" && (
                <BatteryInsights
                  batteryCapacity={project?.battery_capacity_kwh || 0}
                  batteryCycles={simulation.results?.battery_cycles || 0}
                  selfConsumption={simulation.results?.self_consumption_kwh || 0}
                  pvGeneration={simulation.results?.pv_generation_kwh || 0}
                  annualSavings={simulation.results?.annual_savings_eur || 0}
                />
              )}

              {resultsView === "financial" && (
                <FinancialAnalysis
                  annualSavings={simulation.results?.annual_savings_eur || 0}
                  paybackYears={simulation.results?.payback_period_years || 0}
                  pvPeakKw={project?.pv_peak_power_kw || 0}
                  batteryCapacityKwh={project?.battery_capacity_kwh || 0}
                  electricityPrice={project?.electricity_price_eur_kwh || 0.30}
                  totalSavings={simulation.results?.total_savings_eur}
                  npvEur={simulation.results?.npv_eur}
                  irrPercent={simulation.results?.irr_percent}
                />
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4 pt-4 border-t border-slate-200">
              <button
                onClick={runSimulation}
                disabled={isSimulating}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isSimulating ? "animate-spin" : ""}`} />
                Neu berechnen
              </button>
              <button
                onClick={() => generateOffer.mutate()}
                disabled={generateOffer.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {generateOffer.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
                Angebot erstellen
              </button>
            </div>
          </div>
        )}

        {activeTab === "offer" && simulation && (
          <div className="card max-w-3xl mx-auto">
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-slate-900 mb-2">
                Angebot generieren
              </h3>
              <p className="text-slate-500 mb-6 max-w-md mx-auto">
                Erstellen Sie ein professionelles Angebot mit KI-generiertem Text,
                detaillierter Wirtschaftlichkeitsberechnung und Komponentenliste.
              </p>
              <button
                onClick={() => generateOffer.mutate()}
                disabled={generateOffer.isPending}
                className="btn-primary inline-flex items-center gap-2"
              >
                {generateOffer.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Wird erstellt...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Mit KI generieren
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
