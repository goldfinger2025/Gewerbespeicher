"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Battery,
  Sun,
  Zap,
  TrendingUp,
  Leaf,
  Euro,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

interface SimulationKPIs {
  pv_generation_kwh: number;
  self_consumption_kwh: number;
  grid_import_kwh: number;
  grid_export_kwh: number;
  autonomy_degree_percent: number;
  self_consumption_ratio_percent?: number;
  annual_savings_eur: number;
  payback_period_years: number;
  battery_cycles: number;
  total_investment_eur?: number;
}

interface SimulationResultsProps {
  results: SimulationKPIs;
  projectName?: string;
}

// Colors
const COLORS = {
  solar: "#f59e0b",
  battery: "#10b981",
  grid: "#3b82f6",
  export: "#8b5cf6",
  import: "#ef4444",
  savings: "#22c55e",
};

export function SimulationResults({ results, projectName }: SimulationResultsProps) {
  // Generate monthly data for visualization
  const monthlyData = useMemo(() => {
    const months = [
      "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
      "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"
    ];
    
    // Seasonal factors for Germany
    const pvFactors = [0.4, 0.5, 0.8, 1.1, 1.3, 1.4, 1.4, 1.3, 1.0, 0.7, 0.4, 0.3];
    const avgMonthlyPV = results.pv_generation_kwh / 12;
    const avgMonthlyConsumption = (results.self_consumption_kwh + results.grid_import_kwh) / 12;
    
    return months.map((month, i) => ({
      month,
      pv_erzeugung: Math.round(avgMonthlyPV * pvFactors[i]),
      eigenverbrauch: Math.round(avgMonthlyConsumption * 0.85 * (0.8 + pvFactors[i] * 0.2)),
      netzeinspeisung: Math.round(avgMonthlyPV * pvFactors[i] * 0.3),
      netzbezug: Math.round(avgMonthlyConsumption * 0.3 * (1.2 - pvFactors[i] * 0.3)),
    }));
  }, [results]);

  // Energy flow data for pie chart
  const energyFlowData = [
    { name: "Eigenverbrauch", value: results.self_consumption_kwh, color: COLORS.battery },
    { name: "Netzeinspeisung", value: results.grid_export_kwh, color: COLORS.export },
    { name: "Netzbezug", value: results.grid_import_kwh, color: COLORS.import },
  ];

  // Calculate CO2 savings (approx. 400g CO2/kWh in Germany)
  const co2SavingsKg = results.self_consumption_kwh * 0.4;
  const co2SavingsTons = co2SavingsKg / 1000;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            Simulationsergebnisse
          </h2>
          {projectName && (
            <p className="text-slate-500">{projectName}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Clock className="w-4 h-4" />
          Jahressimulation
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Autarkiegrad */}
        <div className="metric-card bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
          <div className="flex items-center gap-2 text-emerald-600 mb-2">
            <Battery className="w-5 h-5" />
            <span className="text-sm font-medium">Autarkiegrad</span>
          </div>
          <div className="metric-value text-emerald-700">
            {results.autonomy_degree_percent.toFixed(0)}%
          </div>
          <p className="text-xs text-emerald-600 mt-1">
            Unabhängigkeit vom Netz
          </p>
        </div>

        {/* Jährliche Einsparung */}
        <div className="metric-card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <Euro className="w-5 h-5" />
            <span className="text-sm font-medium">Einsparung/Jahr</span>
          </div>
          <div className="metric-value text-blue-700">
            {results.annual_savings_eur.toLocaleString("de-DE")} €
          </div>
          <p className="text-xs text-blue-600 mt-1 flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" />
            gegenüber Netzbezug
          </p>
        </div>

        {/* Amortisation */}
        <div className="metric-card bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
          <div className="flex items-center gap-2 text-amber-600 mb-2">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">Amortisation</span>
          </div>
          <div className="metric-value text-amber-700">
            {results.payback_period_years.toFixed(1)} Jahre
          </div>
          <p className="text-xs text-amber-600 mt-1">
            bis zur Kostendeckung
          </p>
        </div>

        {/* CO2 Einsparung */}
        <div className="metric-card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <div className="flex items-center gap-2 text-green-600 mb-2">
            <Leaf className="w-5 h-5" />
            <span className="text-sm font-medium">CO₂ Einsparung</span>
          </div>
          <div className="metric-value text-green-700">
            {co2SavingsTons.toFixed(1)} t
          </div>
          <p className="text-xs text-green-600 mt-1">
            pro Jahr
          </p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Energy Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sun className="w-5 h-5 text-amber-500" />
            Monatlicher Energieverlauf
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={monthlyData}>
              <defs>
                <linearGradient id="colorPV" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.solar} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS.solar} stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="colorEigen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.battery} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS.battery} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} tickFormatter={(v) => `${v} kWh`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} kWh`]}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="pv_erzeugung"
                name="PV-Erzeugung"
                stroke={COLORS.solar}
                fill="url(#colorPV)"
              />
              <Area
                type="monotone"
                dataKey="eigenverbrauch"
                name="Eigenverbrauch"
                stroke={COLORS.battery}
                fill="url(#colorEigen)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Energy Distribution Pie */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-500" />
            Energieverteilung
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={energyFlowData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {energyFlowData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} kWh`]}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Grid Exchange Bar Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            Netzaustausch pro Monat
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} kWh`]}
              />
              <Legend />
              <Bar dataKey="netzeinspeisung" name="Einspeisung" fill={COLORS.export} />
              <Bar dataKey="netzbezug" name="Bezug" fill={COLORS.import} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Detailed KPIs */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            Detaillierte Kennzahlen
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-slate-100">
              <span className="text-slate-600 flex items-center gap-2">
                <Sun className="w-4 h-4 text-amber-500" />
                PV-Erzeugung
              </span>
              <span className="font-semibold">
                {results.pv_generation_kwh.toLocaleString("de-DE")} kWh/Jahr
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-100">
              <span className="text-slate-600 flex items-center gap-2">
                <Battery className="w-4 h-4 text-emerald-500" />
                Eigenverbrauch
              </span>
              <span className="font-semibold">
                {results.self_consumption_kwh.toLocaleString("de-DE")} kWh/Jahr
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-100">
              <span className="text-slate-600 flex items-center gap-2">
                <ArrowUpRight className="w-4 h-4 text-purple-500" />
                Netzeinspeisung
              </span>
              <span className="font-semibold">
                {results.grid_export_kwh.toLocaleString("de-DE")} kWh/Jahr
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-100">
              <span className="text-slate-600 flex items-center gap-2">
                <ArrowDownRight className="w-4 h-4 text-red-500" />
                Netzbezug
              </span>
              <span className="font-semibold">
                {results.grid_import_kwh.toLocaleString("de-DE")} kWh/Jahr
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-100">
              <span className="text-slate-600 flex items-center gap-2">
                <Battery className="w-4 h-4 text-blue-500" />
                Speicher-Zyklen
              </span>
              <span className="font-semibold">
                {results.battery_cycles.toFixed(0)} Zyklen/Jahr
              </span>
            </div>
            {results.total_investment_eur && (
              <div className="flex justify-between items-center py-2">
                <span className="text-slate-600 flex items-center gap-2">
                  <Euro className="w-4 h-4 text-slate-500" />
                  Investition (geschätzt)
                </span>
                <span className="font-semibold">
                  {results.total_investment_eur.toLocaleString("de-DE")} €
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Box */}
      <div className="bg-gradient-to-r from-blue-600 to-emerald-600 rounded-xl p-6 text-white">
        <h3 className="text-xl font-bold mb-4">📊 Zusammenfassung</h3>
        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <p className="text-blue-100 text-sm">Mit diesem System decken Sie</p>
            <p className="text-3xl font-bold">{results.autonomy_degree_percent.toFixed(0)}%</p>
            <p className="text-blue-100 text-sm">Ihres Strombedarfs selbst</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">Sie sparen jährlich</p>
            <p className="text-3xl font-bold">{results.annual_savings_eur.toLocaleString("de-DE")} €</p>
            <p className="text-blue-100 text-sm">an Stromkosten</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">Die Investition amortisiert sich in</p>
            <p className="text-3xl font-bold">{results.payback_period_years.toFixed(1)} Jahren</p>
            <p className="text-blue-100 text-sm">durch eingesparte Kosten</p>
          </div>
        </div>
      </div>
    </div>
  );
}
