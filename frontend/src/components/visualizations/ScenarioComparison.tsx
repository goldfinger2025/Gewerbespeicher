"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import {
  TrendingUp,
  Battery,
  Sun,
  Euro,
  Leaf,
  CheckCircle,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { ComparisonResult, ScenarioData } from "@/types/simulation";

interface ScenarioComparisonProps {
  comparison: ComparisonResult;
  onSelectScenario?: (scenario: ScenarioData) => void;
}

const SCENARIO_COLORS = {
  "Basis": "#3b82f6",
  "ROI-Optimiert": "#10b981",
  "Autarkie-Optimiert": "#8b5cf6",
};

const MONTH_NAMES = [
  "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
  "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"
];

export function ScenarioComparison({ comparison, onSelectScenario }: ScenarioComparisonProps) {
  // Prepare data for bar charts
  const investmentData = comparison.scenarios.map(s => ({
    name: s.name,
    investment: s.investment_eur,
    fill: SCENARIO_COLORS[s.name as keyof typeof SCENARIO_COLORS] || "#64748b",
  }));

  const savingsData = comparison.scenarios.map(s => ({
    name: s.name,
    savings: s.annual_savings_eur,
    fill: SCENARIO_COLORS[s.name as keyof typeof SCENARIO_COLORS] || "#64748b",
  }));

  // Prepare radar chart data for comparing scenarios
  const radarData = useMemo(() => {
    const maxValues = {
      autonomy: Math.max(...comparison.scenarios.map(s => s.autonomy_percent)),
      savings: Math.max(...comparison.scenarios.map(s => s.annual_savings_eur)),
      npv: Math.max(...comparison.scenarios.map(s => s.npv_20y_eur)),
      co2: Math.max(...comparison.scenarios.map(s => s.co2_savings_tons)),
      payback: Math.max(...comparison.scenarios.map(s => s.payback_years)),
    };

    const categories = [
      { key: "autonomy", label: "Autarkie", unit: "%" },
      { key: "savings", label: "Einsparung", unit: "€" },
      { key: "npv", label: "NPV (20J)", unit: "€" },
      { key: "co2", label: "CO₂", unit: "t" },
      { key: "payback", label: "ROI Speed", unit: "" },
    ];

    return categories.map(cat => {
      const result: Record<string, string | number> = { category: cat.label };
      comparison.scenarios.forEach(s => {
        let value: number;
        switch (cat.key) {
          case "autonomy":
            value = (s.autonomy_percent / maxValues.autonomy) * 100;
            break;
          case "savings":
            value = (s.annual_savings_eur / maxValues.savings) * 100;
            break;
          case "npv":
            value = (s.npv_20y_eur / maxValues.npv) * 100;
            break;
          case "co2":
            value = (s.co2_savings_tons / maxValues.co2) * 100;
            break;
          case "payback":
            // Inverse: shorter payback = better
            value = ((maxValues.payback - s.payback_years + 1) / maxValues.payback) * 100;
            break;
          default:
            value = 0;
        }
        result[s.name] = Math.round(value);
      });
      return result;
    });
  }, [comparison.scenarios]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-amber-500" />
            Szenarien-Vergleich
          </h2>
          <p className="text-slate-500 mt-1">
            Vergleichen Sie verschiedene Systemkonfigurationen
          </p>
        </div>
      </div>

      {/* Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {comparison.scenarios.map((scenario, index) => (
          <div
            key={scenario.name}
            className={`relative card border-2 transition-all hover:shadow-lg cursor-pointer ${
              index === 0 ? "border-blue-300 bg-blue-50/50" :
              index === 1 ? "border-emerald-300 bg-emerald-50/50" :
              "border-purple-300 bg-purple-50/50"
            }`}
            onClick={() => onSelectScenario?.(scenario)}
          >
            {/* Badge */}
            <div className={`absolute -top-3 left-4 px-3 py-1 rounded-full text-xs font-semibold text-white ${
              index === 0 ? "bg-blue-500" :
              index === 1 ? "bg-emerald-500" :
              "bg-purple-500"
            }`}>
              {scenario.name}
            </div>

            <div className="pt-4">
              <p className="text-sm text-slate-600 mb-4">{scenario.description}</p>

              {/* System Size */}
              <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-2">
                  <Sun className="w-4 h-4 text-amber-500" />
                  <span className="font-semibold">{scenario.pv_kw} kWp</span>
                </div>
                <div className="flex items-center gap-2">
                  <Battery className="w-4 h-4 text-emerald-500" />
                  <span className="font-semibold">{scenario.battery_kwh} kWh</span>
                </div>
              </div>

              {/* Key Metrics */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Investition</span>
                  <span className="font-semibold">{scenario.investment_eur.toLocaleString("de-DE")} €</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Autarkie</span>
                  <span className="font-semibold text-emerald-600">{scenario.autonomy_percent.toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Einsparung/Jahr</span>
                  <span className="font-semibold text-blue-600">{scenario.annual_savings_eur.toLocaleString("de-DE")} €</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Amortisation</span>
                  <span className="font-semibold">{scenario.payback_years.toFixed(1)} Jahre</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">NPV (20J)</span>
                  <span className="font-semibold text-green-600">{scenario.npv_20y_eur.toLocaleString("de-DE")} €</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">CO₂-Einsparung</span>
                  <span className="font-semibold">{scenario.co2_savings_tons.toFixed(1)} t/Jahr</span>
                </div>
              </div>

              {/* Highlight */}
              <div className={`mt-4 p-3 rounded-lg text-sm font-medium ${
                index === 0 ? "bg-blue-100 text-blue-700" :
                index === 1 ? "bg-emerald-100 text-emerald-700" :
                "bg-purple-100 text-purple-700"
              }`}>
                <CheckCircle className="w-4 h-4 inline mr-2" />
                {scenario.highlight}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Investment Comparison */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Euro className="w-5 h-5 text-slate-500" />
            Investitionsvergleich
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={investmentData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k €`} />
              <YAxis type="category" dataKey="name" width={120} />
              <Tooltip
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} €`, "Investition"]}
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="investment" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                {investmentData.map((entry, index) => (
                  <rect key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Radar Comparison */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-slate-500" />
            Leistungsvergleich
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
              {comparison.scenarios.map((s, i) => (
                <Radar
                  key={s.name}
                  name={s.name}
                  dataKey={s.name}
                  stroke={Object.values(SCENARIO_COLORS)[i]}
                  fill={Object.values(SCENARIO_COLORS)[i]}
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              ))}
              <Legend />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Annual Savings */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Euro className="w-5 h-5 text-emerald-500" />
            Jährliche Einsparungen
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={savingsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k €`} />
              <Tooltip
                formatter={(value: number) => [`${value.toLocaleString("de-DE")} €`, "Einsparung/Jahr"]}
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="savings" fill="#10b981" radius={[4, 4, 0, 0]}>
                {savingsData.map((entry, index) => (
                  <rect key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* CO2 Comparison */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Leaf className="w-5 h-5 text-green-500" />
            CO₂-Einsparungen (pro Jahr)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={comparison.scenarios.map(s => ({
              name: s.name,
              co2: s.co2_savings_tons,
              fill: SCENARIO_COLORS[s.name as keyof typeof SCENARIO_COLORS] || "#64748b",
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(v) => `${v.toFixed(1)} t`} />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)} t`, "CO₂/Jahr"]}
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="co2" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recommendation Box */}
      <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl p-6 text-white">
        <h3 className="text-xl font-bold mb-3 flex items-center gap-2">
          <Sparkles className="w-6 h-6" />
          KI-Empfehlung
        </h3>
        <p className="text-amber-50 mb-4">{comparison.recommendation}</p>
        <div className="bg-white/20 rounded-lg p-4 text-sm">
          <p className="text-amber-100">{comparison.comparison_summary}</p>
        </div>
      </div>
    </div>
  );
}
