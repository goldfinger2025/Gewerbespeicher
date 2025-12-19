'use client';

import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  Cell,
} from 'recharts';
import { Battery, BatteryCharging, Zap, RefreshCw, TrendingUp, AlertTriangle } from 'lucide-react';

interface BatteryInsightsProps {
  batteryCapacity: number;       // kWh
  batteryPowerKw: number;        // kW Nennleistung
  batteryCycles: number;         // Zyklen pro Jahr
  selfConsumption: number;       // kWh/Jahr Eigenverbrauch
  pvGeneration: number;          // kWh/Jahr PV-Erzeugung
  pvPeakKw: number;              // kWp Nennleistung
  annualSavings: number;         // EUR/Jahr
  // Neue Kennzahlen
  batteryChargingHours?: number;
  batteryDischargingHours?: number;
  batteryOperatingHours?: number;
  batteryFullLoadHours?: number;
  batteryUtilizationPercent?: number;
  pvFullLoadHours?: number;
}

export function BatteryInsights({
  batteryCapacity,
  batteryPowerKw,
  batteryCycles,
  selfConsumption,
  pvGeneration,
  pvPeakKw,
  annualSavings,
  batteryChargingHours,
  batteryDischargingHours,
  batteryOperatingHours,
  batteryFullLoadHours,
  batteryUtilizationPercent,
  pvFullLoadHours,
}: BatteryInsightsProps) {
  // Generate synthetic daily SOC pattern (typical summer day)
  const dailySOCData = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => i);

    return hours.map((hour) => {
      let soc = 20; // Start at 20%

      // Morning: slowly charging from overnight low
      if (hour >= 0 && hour < 6) {
        soc = 15 + hour * 1;
      }
      // Morning peak: PV kicks in, rapid charging
      else if (hour >= 6 && hour < 12) {
        soc = 20 + (hour - 6) * 13;
      }
      // Midday: fully charged
      else if (hour >= 12 && hour < 14) {
        soc = 95;
      }
      // Afternoon: slight discharge for consumption
      else if (hour >= 14 && hour < 18) {
        soc = 95 - (hour - 14) * 10;
      }
      // Evening peak: heavy discharge
      else if (hour >= 18 && hour < 22) {
        soc = 55 - (hour - 18) * 12;
      }
      // Night: minimal activity
      else {
        soc = 20 - (hour - 22) * 2;
      }

      // Add some variation
      soc = Math.max(10, Math.min(100, soc + (Math.random() - 0.5) * 5));

      return {
        hour: `${hour.toString().padStart(2, '0')}:00`,
        soc: Math.round(soc),
        socKwh: Math.round((soc / 100) * batteryCapacity * 10) / 10,
      };
    });
  }, [batteryCapacity]);

  // Monthly cycle distribution
  const monthlyCycleData = useMemo(() => {
    const monthNames = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
    // Seasonal distribution: more cycles in summer due to higher PV yield
    const seasonalFactors = [0.6, 0.7, 0.9, 1.1, 1.2, 1.3, 1.3, 1.2, 1.0, 0.8, 0.6, 0.5];
    const avgMonthly = batteryCycles / 12;

    return monthNames.map((month, i) => ({
      month,
      cycles: Math.round(avgMonthly * seasonalFactors[i]),
      vollzyklen: Math.round(avgMonthly * seasonalFactors[i] * 0.7),
      teilzyklen: Math.round(avgMonthly * seasonalFactors[i] * 0.3),
    }));
  }, [batteryCycles]);

  // Calculate battery health metrics
  const batteryMetrics = useMemo(() => {
    const totalCycles = batteryCycles;
    const ratedCycles = 6000; // Typical LFP warranty
    const yearlyDegradation = (totalCycles / ratedCycles) * 100;
    const estimatedLifeYears = Math.round(ratedCycles / totalCycles);
    const dailyAvgCycles = totalCycles / 365;

    // Nutze berechnete Werte wenn vorhanden, sonst Fallback
    const utilizationRate = batteryUtilizationPercent ?? (dailyAvgCycles / 1.5) * 100;
    const fullLoadHours = batteryFullLoadHours ?? (totalCycles * batteryCapacity / (batteryPowerKw || 1));
    const operatingHours = batteryOperatingHours ?? Math.round(fullLoadHours * 1.5);
    const chargingHours = batteryChargingHours ?? Math.round(operatingHours * 0.45);
    const dischargingHours = batteryDischargingHours ?? Math.round(operatingHours * 0.55);

    return {
      yearlyDegradation: Math.round(yearlyDegradation * 10) / 10,
      estimatedLifeYears,
      dailyAvgCycles: Math.round(dailyAvgCycles * 100) / 100,
      utilizationRate: Math.min(100, Math.round(utilizationRate)),
      savingsPerCycle: Math.round((annualSavings / totalCycles) * 100) / 100,
      // Neue Kennzahlen
      fullLoadHours: Math.round(fullLoadHours),
      operatingHours: Math.round(operatingHours),
      chargingHours: Math.round(chargingHours),
      dischargingHours: Math.round(dischargingHours),
      pvFullLoadHours: pvFullLoadHours ?? Math.round(pvGeneration / (pvPeakKw || 1)),
    };
  }, [batteryCycles, annualSavings, batteryCapacity, batteryPowerKw, pvGeneration, pvPeakKw,
      batteryUtilizationPercent, batteryFullLoadHours, batteryOperatingHours,
      batteryChargingHours, batteryDischargingHours, pvFullLoadHours]);

  const formatNumber = (n: number) =>
    n.toLocaleString('de-DE', { maximumFractionDigits: 1 });

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-emerald-600 mb-2">
            <Battery className="w-5 h-5" />
            <span className="text-sm font-medium">Kapazität</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{batteryCapacity} kWh</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <RefreshCw className="w-5 h-5" />
            <span className="text-sm font-medium">Zyklen/Jahr</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{batteryCycles}</p>
          <p className="text-xs text-slate-500 mt-1">{batteryMetrics.dailyAvgCycles}/Tag</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-amber-600 mb-2">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">Nutzungsgrad</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{batteryMetrics.utilizationRate}%</p>
          <p className="text-xs text-slate-500 mt-1">
            {batteryMetrics.utilizationRate > 80 ? 'Optimal' : 'Potenzial vorhanden'}
          </p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-violet-600 mb-2">
            <Zap className="w-5 h-5" />
            <span className="text-sm font-medium">Lebensdauer</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">~{batteryMetrics.estimatedLifeYears} Jahre</p>
          <p className="text-xs text-slate-500 mt-1">bei 6.000 Zyklen</p>
        </div>
      </div>

      {/* Daily SOC Pattern */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <BatteryCharging className="w-5 h-5 text-emerald-600" />
          Typischer Tagesverlauf (Ladezustand)
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailySOCData}>
              <defs>
                <linearGradient id="socGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                interval={2}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload?.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
                        <p className="font-medium text-slate-800">{data.hour} Uhr</p>
                        <p className="text-emerald-600">SOC: {data.soc}%</p>
                        <p className="text-slate-600 text-sm">{data.socKwh} kWh</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="soc"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#socGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="text-sm text-slate-500 mt-2 text-center">
          Simulierter Ladezustand an einem typischen Sommertag
        </p>
      </div>

      {/* Monthly Cycle Distribution */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-blue-600" />
          Monatliche Zyklenverteilung
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlyCycleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload?.length) {
                    return (
                      <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
                        <p className="font-medium text-slate-800">{label}</p>
                        <p className="text-blue-600">Vollzyklen: {payload[0].value}</p>
                        <p className="text-emerald-600">Teilzyklen: {payload[1].value}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend
                wrapperStyle={{ paddingTop: '10px' }}
                formatter={(value) => (
                  <span className="text-sm text-slate-600">
                    {value === 'vollzyklen' ? 'Vollzyklen' : 'Teilzyklen'}
                  </span>
                )}
              />
              <Bar dataKey="vollzyklen" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} />
              <Bar dataKey="teilzyklen" stackId="a" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Volllaststunden und Betriebsstunden */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-500" />
          Volllaststunden & Betriebsstunden
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-amber-50 rounded-lg p-4">
            <p className="text-sm text-slate-600">PV-Volllaststunden</p>
            <p className="text-2xl font-bold text-amber-700">{formatNumber(batteryMetrics.pvFullLoadHours)} h</p>
            <p className="text-xs text-slate-500">kWh/kWp (Jahresertrag)</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-slate-600">Batterie-Volllaststunden</p>
            <p className="text-2xl font-bold text-blue-700">{formatNumber(batteryMetrics.fullLoadHours)} h</p>
            <p className="text-xs text-slate-500">bei Nennleistung</p>
          </div>
          <div className="bg-emerald-50 rounded-lg p-4">
            <p className="text-sm text-slate-600">Betriebsstunden gesamt</p>
            <p className="text-2xl font-bold text-emerald-700">{formatNumber(batteryMetrics.operatingHours)} h</p>
            <p className="text-xs text-slate-500">Laden + Entladen</p>
          </div>
          <div className="bg-violet-50 rounded-lg p-4">
            <p className="text-sm text-slate-600">Nutzungsgrad</p>
            <p className="text-2xl font-bold text-violet-700">{batteryMetrics.utilizationRate}%</p>
            <p className="text-xs text-slate-500">von 8.760 h/Jahr</p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 bg-slate-50 rounded-lg p-3">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <div>
              <p className="text-sm font-medium text-slate-700">Ladestunden</p>
              <p className="text-lg font-bold text-slate-800">{formatNumber(batteryMetrics.chargingHours)} h/Jahr</p>
            </div>
          </div>
          <div className="flex items-center gap-3 bg-slate-50 rounded-lg p-3">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <div>
              <p className="text-sm font-medium text-slate-700">Entladestunden</p>
              <p className="text-lg font-bold text-slate-800">{formatNumber(batteryMetrics.dischargingHours)} h/Jahr</p>
            </div>
          </div>
        </div>
      </div>

      {/* Battery Health Info */}
      <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl p-6 border border-emerald-100">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          Batterie-Analyse
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-slate-600">Jährliche Degradation</p>
            <p className="text-xl font-bold text-slate-800">{batteryMetrics.yearlyDegradation}%</p>
            <p className="text-xs text-slate-500">der nominellen Kapazität</p>
          </div>
          <div>
            <p className="text-sm text-slate-600">Ersparnis pro Zyklus</p>
            <p className="text-xl font-bold text-slate-800">{formatNumber(batteryMetrics.savingsPerCycle)} EUR</p>
            <p className="text-xs text-slate-500">wirtschaftlicher Nutzen</p>
          </div>
          <div>
            <p className="text-sm text-slate-600">Durchsatz pro Jahr</p>
            <p className="text-xl font-bold text-slate-800">
              {formatNumber(batteryCycles * batteryCapacity)} kWh
            </p>
            <p className="text-xs text-slate-500">gespeicherte Energie</p>
          </div>
        </div>
      </div>
    </div>
  );
}
