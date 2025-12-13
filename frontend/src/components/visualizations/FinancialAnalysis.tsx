'use client';

import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
} from 'recharts';
import { Euro, TrendingUp, PiggyBank, Calendar, Target, ArrowUpRight } from 'lucide-react';

interface FinancialAnalysisProps {
  annualSavings: number;         // EUR/Jahr
  paybackYears: number;          // Jahre
  investmentCost?: number;       // EUR (optional, wird berechnet)
  pvPeakKw: number;              // kWp
  batteryCapacityKwh: number;    // kWh
  electricityPrice: number;      // EUR/kWh
}

export function FinancialAnalysis({
  annualSavings,
  paybackYears,
  investmentCost,
  pvPeakKw,
  batteryCapacityKwh,
  electricityPrice,
}: FinancialAnalysisProps) {
  // Calculate investment if not provided
  const totalInvestment = useMemo(() => {
    if (investmentCost) return investmentCost;
    // Estimate: ~1000 EUR/kWp PV + ~500 EUR/kWh Battery
    return pvPeakKw * 1000 + batteryCapacityKwh * 500;
  }, [investmentCost, pvPeakKw, batteryCapacityKwh]);

  // Generate 25-year cashflow projection
  const cashflowData = useMemo(() => {
    const years = Array.from({ length: 26 }, (_, i) => i);
    const discountRate = 0.03; // 3% discount rate
    const degradationRate = 0.005; // 0.5% annual degradation
    const electricityPriceIncrease = 0.03; // 3% annual price increase

    let cumulativeSavings = 0;
    let cumulativeNPV = 0;

    return years.map((year) => {
      if (year === 0) {
        return {
          year: 0,
          savings: 0,
          cumulativeSavings: -totalInvestment,
          npv: -totalInvestment,
          cumulativeNPV: -totalInvestment,
          cashflow: -totalInvestment,
        };
      }

      // Adjust for degradation and price increase
      const degradationFactor = Math.pow(1 - degradationRate, year);
      const priceFactor = Math.pow(1 + electricityPriceIncrease, year);
      const yearSavings = annualSavings * degradationFactor * priceFactor;

      // NPV calculation
      const discountFactor = Math.pow(1 + discountRate, year);
      const npvSavings = yearSavings / discountFactor;

      cumulativeSavings += yearSavings;
      cumulativeNPV += npvSavings;

      return {
        year,
        savings: Math.round(yearSavings),
        cumulativeSavings: Math.round(cumulativeSavings - totalInvestment),
        npv: Math.round(npvSavings),
        cumulativeNPV: Math.round(cumulativeNPV - totalInvestment),
        cashflow: Math.round(yearSavings),
      };
    });
  }, [annualSavings, totalInvestment]);

  // Calculate key financial metrics
  const financialMetrics = useMemo(() => {
    const finalData = cashflowData[cashflowData.length - 1];
    const totalReturn = finalData.cumulativeSavings;
    const roi = ((totalReturn + totalInvestment) / totalInvestment) * 100;
    const irr = ((Math.pow(1 + totalReturn / totalInvestment, 1 / 25) - 1) * 100);

    // Find breakeven year
    const breakevenYear = cashflowData.findIndex((d) => d.cumulativeSavings >= 0);

    return {
      totalReturn: Math.round(totalReturn),
      roi: Math.round(roi),
      irr: Math.round(irr * 10) / 10,
      npv25: finalData.cumulativeNPV,
      breakevenYear: breakevenYear > 0 ? breakevenYear : paybackYears,
    };
  }, [cashflowData, totalInvestment, paybackYears]);

  // Monthly savings breakdown (first year)
  const monthlySavingsData = useMemo(() => {
    const monthNames = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
    const seasonalFactors = [0.5, 0.6, 0.9, 1.1, 1.3, 1.4, 1.4, 1.3, 1.0, 0.7, 0.5, 0.4];
    const avgMonthly = annualSavings / 12;

    return monthNames.map((month, i) => ({
      month,
      savings: Math.round(avgMonthly * seasonalFactors[i]),
    }));
  }, [annualSavings]);

  const formatEuro = (n: number) =>
    n.toLocaleString('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

  const formatNumber = (n: number) =>
    n.toLocaleString('de-DE', { maximumFractionDigits: 0 });

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <Euro className="w-5 h-5" />
            <span className="text-sm font-medium">Investition</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{formatEuro(totalInvestment)}</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-emerald-600 mb-2">
            <PiggyBank className="w-5 h-5" />
            <span className="text-sm font-medium">Jährl. Ersparnis</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{formatEuro(annualSavings)}</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-amber-600 mb-2">
            <Calendar className="w-5 h-5" />
            <span className="text-sm font-medium">Amortisation</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{paybackYears.toFixed(1)} Jahre</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 text-violet-600 mb-2">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">ROI (25 J.)</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">{financialMetrics.roi}%</p>
        </div>
      </div>

      {/* Cumulative Savings Chart */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-emerald-600" />
          Kumulierte Ersparnis (25 Jahre)
        </h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={cashflowData}>
              <defs>
                <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                  <stop offset="50%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="negativeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0} />
                  <stop offset="50%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.8} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                tickFormatter={(v) => `${v}J`}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload?.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
                        <p className="font-medium text-slate-800">Jahr {data.year}</p>
                        <p className={data.cumulativeSavings >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                          Kumuliert: {formatEuro(data.cumulativeSavings)}
                        </p>
                        {data.year > 0 && (
                          <p className="text-slate-600 text-sm">
                            Ersparnis: {formatEuro(data.savings)}
                          </p>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
              <ReferenceLine
                x={financialMetrics.breakevenYear}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                label={{
                  value: 'Break-Even',
                  position: 'top',
                  fill: '#f59e0b',
                  fontSize: 11,
                }}
              />
              <Area
                type="monotone"
                dataKey="cumulativeSavings"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#savingsGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-slate-600">Kumulierte Ersparnis</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-amber-500" />
            <span className="text-slate-600">Break-Even Punkt</span>
          </div>
        </div>
      </div>

      {/* Monthly Savings Breakdown */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Euro className="w-5 h-5 text-blue-600" />
          Monatliche Ersparnis (Jahr 1)
        </h3>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlySavingsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                tickFormatter={(v) => `${v}€`}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload?.length) {
                    return (
                      <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
                        <p className="font-medium text-slate-800">{label}</p>
                        <p className="text-blue-600">{formatEuro(payload[0].value as number)}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="savings" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Financial Summary Box */}
      <div className="bg-gradient-to-r from-blue-600 to-emerald-600 rounded-xl p-6 text-white">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <ArrowUpRight className="w-5 h-5" />
          25-Jahres-Prognose
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-blue-100 text-sm">Gesamtersparnis</p>
            <p className="text-2xl font-bold">
              {formatEuro(financialMetrics.totalReturn + totalInvestment)}
            </p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">Nettogewinn</p>
            <p className="text-2xl font-bold">{formatEuro(financialMetrics.totalReturn)}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">NPV (3% Diskont)</p>
            <p className="text-2xl font-bold">{formatEuro(financialMetrics.npv25)}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">Effektive Rendite</p>
            <p className="text-2xl font-bold">{financialMetrics.irr}% p.a.</p>
          </div>
        </div>
      </div>

      {/* Assumptions Note */}
      <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
        <p className="text-sm text-slate-600">
          <span className="font-medium">Annahmen:</span> 3% jährliche Strompreissteigerung,
          0,5% jährliche Anlagendegradation, 3% Diskontierungszins.
          Strompreis aktuell: {electricityPrice.toFixed(2)} EUR/kWh.
        </p>
      </div>
    </div>
  );
}
