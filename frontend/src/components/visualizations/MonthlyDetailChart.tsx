"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  Sun,
  Battery,
  Zap,
  TrendingUp,
  Calendar,
} from "lucide-react";
import { MonthlySummary } from "@/types/simulation";

interface MonthlyDetailChartProps {
  monthlyData: MonthlySummary[];
  electricityPrice?: number;
  feedInTariff?: number;
}

const MONTH_NAMES = [
  "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
  "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"
];

const COLORS = {
  pv: "#f59e0b",
  consumption: "#64748b",
  selfConsumption: "#10b981",
  gridExport: "#8b5cf6",
  gridImport: "#ef4444",
  autonomy: "#3b82f6",
  savings: "#22c55e",
};

export function MonthlyDetailChart({
  monthlyData,
  electricityPrice = 0.30,
  feedInTariff = 0.08,
}: MonthlyDetailChartProps) {
  // Transform data with month names and calculated values
  const chartData = useMemo(() => {
    return monthlyData.map((m) => {
      const savings = (m.self_consumption_kwh * electricityPrice) +
                      (m.grid_export_kwh * feedInTariff);
      return {
        month: MONTH_NAMES[m.month - 1],
        monthNum: m.month,
        pv_erzeugung: Math.round(m.pv_generation_kwh),
        verbrauch: Math.round(m.consumption_kwh),
        eigenverbrauch: Math.round(m.self_consumption_kwh),
        netzeinspeisung: Math.round(m.grid_export_kwh),
        netzbezug: Math.round(m.grid_import_kwh),
        autarkie: m.autonomy_percent ?? Math.round(
          ((m.consumption_kwh - m.grid_import_kwh) / m.consumption_kwh) * 100
        ),
        einsparung: Math.round(savings),
      };
    });
  }, [monthlyData, electricityPrice, feedInTariff]);

  // Calculate summary statistics
  const stats = useMemo(() => {
    const totalPV = chartData.reduce((sum, m) => sum + m.pv_erzeugung, 0);
    const totalConsumption = chartData.reduce((sum, m) => sum + m.verbrauch, 0);
    const totalSelfConsumption = chartData.reduce((sum, m) => sum + m.eigenverbrauch, 0);
    const totalExport = chartData.reduce((sum, m) => sum + m.netzeinspeisung, 0);
    const totalImport = chartData.reduce((sum, m) => sum + m.netzbezug, 0);
    const avgAutonomy = chartData.reduce((sum, m) => sum + m.autarkie, 0) / 12;
    const totalSavings = chartData.reduce((sum, m) => sum + m.einsparung, 0);

    // Seasonal breakdown
    const summerMonths = [4, 5, 6, 7, 8]; // Mai-Sep (0-indexed: 4-8)
    const winterMonths = [0, 1, 10, 11]; // Nov-Mär (0-indexed: 0, 1, 10, 11)

    const summerPV = chartData
      .filter((_, i) => summerMonths.includes(i))
      .reduce((sum, m) => sum + m.pv_erzeugung, 0);
    const winterPV = chartData
      .filter((_, i) => winterMonths.includes(i))
      .reduce((sum, m) => sum + m.pv_erzeugung, 0);

    return {
      totalPV,
      totalConsumption,
      totalSelfConsumption,
      totalExport,
      totalImport,
      avgAutonomy,
      totalSavings,
      summerPV,
      winterPV,
      summerShare: (summerPV / totalPV) * 100,
    };
  }, [chartData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-blue-500" />
            Monatliche Analyse
          </h2>
          <p className="text-slate-500 mt-1">
            Detaillierte Aufschlüsselung nach Monaten
          </p>
        </div>
      </div>

      {/* Season Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200">
          <div className="flex items-center gap-2 text-amber-600 mb-2">
            <Sun className="w-5 h-5" />
            <span className="text-sm font-medium">Sommer-Ertrag</span>
          </div>
          <div className="text-2xl font-bold text-amber-700">
            {stats.summerPV.toLocaleString("de-DE")} kWh
          </div>
          <p className="text-xs text-amber-600 mt-1">
            {stats.summerShare.toFixed(0)}% des Jahresertrags
          </p>
        </div>

        <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <Sun className="w-5 h-5" />
            <span className="text-sm font-medium">Winter-Ertrag</span>
          </div>
          <div className="text-2xl font-bold text-blue-700">
            {stats.winterPV.toLocaleString("de-DE")} kWh
          </div>
          <p className="text-xs text-blue-600 mt-1">
            {(100 - stats.summerShare).toFixed(0)}% des Jahresertrags
          </p>
        </div>

        <div className="card bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
          <div className="flex items-center gap-2 text-emerald-600 mb-2">
            <Battery className="w-5 h-5" />
            <span className="text-sm font-medium">Ø Autarkie</span>
          </div>
          <div className="text-2xl font-bold text-emerald-700">
            {stats.avgAutonomy.toFixed(0)}%
          </div>
          <p className="text-xs text-emerald-600 mt-1">
            Jahresdurchschnitt
          </p>
        </div>

        <div className="card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <div className="flex items-center gap-2 text-green-600 mb-2">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">Einsparung/Jahr</span>
          </div>
          <div className="text-2xl font-bold text-green-700">
            {stats.totalSavings.toLocaleString("de-DE")} €
          </div>
          <p className="text-xs text-green-600 mt-1">
            Ø {Math.round(stats.totalSavings / 12)} €/Monat
          </p>
        </div>
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Energy Flow Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            Energiefluss pro Monat
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData}>
              <defs>
                <linearGradient id="colorPVMonth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.pv} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS.pv} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis
                yAxisId="left"
                stroke="#64748b"
                fontSize={12}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke={COLORS.autonomy}
                fontSize={12}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "Autarkie") return [`${value}%`, name];
                  return [`${value.toLocaleString("de-DE")} kWh`, name];
                }}
              />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="pv_erzeugung"
                name="PV-Erzeugung"
                stroke={COLORS.pv}
                fill="url(#colorPVMonth)"
              />
              <Bar
                yAxisId="left"
                dataKey="eigenverbrauch"
                name="Eigenverbrauch"
                fill={COLORS.selfConsumption}
                radius={[4, 4, 0, 0]}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="autarkie"
                name="Autarkie"
                stroke={COLORS.autonomy}
                strokeWidth={3}
                dot={{ fill: COLORS.autonomy, r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Grid Exchange Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-500" />
            Netzaustausch pro Monat
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis
                stroke="#64748b"
                fontSize={12}
                tickFormatter={(v) => `${v.toLocaleString("de-DE")}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} kWh`]}
              />
              <Legend />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar
                dataKey="netzeinspeisung"
                name="Einspeisung"
                fill={COLORS.gridExport}
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="netzbezug"
                name="Netzbezug"
                fill={COLORS.gridImport}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Autonomy Trend */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Battery className="w-5 h-5 text-emerald-500" />
            Autarkiegrad im Jahresverlauf
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorAutonomy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.autonomy} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS.autonomy} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis
                stroke="#64748b"
                fontSize={12}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number) => [`${value.toFixed(0)}%`, "Autarkie"]}
              />
              <ReferenceLine y={stats.avgAutonomy} stroke="#94a3b8" strokeDasharray="5 5" label="Ø" />
              <Area
                type="monotone"
                dataKey="autarkie"
                name="Autarkie"
                stroke={COLORS.autonomy}
                fill="url(#colorAutonomy)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly Savings */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            Monatliche Einsparungen
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
              <YAxis
                stroke="#64748b"
                fontSize={12}
                tickFormatter={(v) => `${v} €`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} €`, "Einsparung"]}
              />
              <Bar
                dataKey="einsparung"
                name="Einsparung"
                fill={COLORS.savings}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monthly Data Table */}
      <div className="card overflow-x-auto">
        <h3 className="text-lg font-semibold mb-4">Monatliche Detaildaten</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 px-3 font-semibold text-slate-600">Monat</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">PV (kWh)</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Verbrauch (kWh)</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Eigenverbrauch (kWh)</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Einspeisung (kWh)</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Netzbezug (kWh)</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Autarkie</th>
              <th className="text-right py-2 px-3 font-semibold text-slate-600">Einsparung</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((row, i) => (
              <tr key={row.month} className={i % 2 === 0 ? "bg-slate-50" : ""}>
                <td className="py-2 px-3 font-medium">{row.month}</td>
                <td className="text-right py-2 px-3 text-amber-600">{row.pv_erzeugung.toLocaleString("de-DE")}</td>
                <td className="text-right py-2 px-3">{row.verbrauch.toLocaleString("de-DE")}</td>
                <td className="text-right py-2 px-3 text-emerald-600">{row.eigenverbrauch.toLocaleString("de-DE")}</td>
                <td className="text-right py-2 px-3 text-purple-600">{row.netzeinspeisung.toLocaleString("de-DE")}</td>
                <td className="text-right py-2 px-3 text-red-600">{row.netzbezug.toLocaleString("de-DE")}</td>
                <td className="text-right py-2 px-3 text-blue-600 font-semibold">{row.autarkie}%</td>
                <td className="text-right py-2 px-3 text-green-600 font-semibold">{row.einsparung} €</td>
              </tr>
            ))}
            {/* Totals Row */}
            <tr className="border-t-2 border-slate-300 font-bold bg-slate-100">
              <td className="py-2 px-3">Gesamt</td>
              <td className="text-right py-2 px-3 text-amber-600">{stats.totalPV.toLocaleString("de-DE")}</td>
              <td className="text-right py-2 px-3">{stats.totalConsumption.toLocaleString("de-DE")}</td>
              <td className="text-right py-2 px-3 text-emerald-600">{stats.totalSelfConsumption.toLocaleString("de-DE")}</td>
              <td className="text-right py-2 px-3 text-purple-600">{stats.totalExport.toLocaleString("de-DE")}</td>
              <td className="text-right py-2 px-3 text-red-600">{stats.totalImport.toLocaleString("de-DE")}</td>
              <td className="text-right py-2 px-3 text-blue-600">Ø {stats.avgAutonomy.toFixed(0)}%</td>
              <td className="text-right py-2 px-3 text-green-600">{stats.totalSavings.toLocaleString("de-DE")} €</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
