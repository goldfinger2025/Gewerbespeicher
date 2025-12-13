'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from 'recharts';
import {
  Sun,
  Battery,
  TrendingUp,
  Leaf,
  Euro,
  Zap,
  FileText,
  CheckCircle,
  Clock,
} from 'lucide-react';
import api from '@/lib/api-client';

export default function AnalyticsPage() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: () => api.getDashboardMetrics('month'),
  });

  const { data: kpis } = useQuery({
    queryKey: ['performance-kpis'],
    queryFn: async () => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/analytics/performance-kpis`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      return response.json();
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="skeleton h-80 rounded-xl" />
          <div className="skeleton h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  const metrics = dashboard?.metrics;
  const trends = dashboard?.monthly_trends || [];

  // Prepare energy distribution data
  const energyData = kpis
    ? [
        { name: 'Eigenverbrauch', value: kpis.total_self_consumption_kwh || 0, color: '#10b981' },
        { name: 'Netzeinspeisung', value: kpis.total_grid_export_kwh || 0, color: '#f59e0b' },
        { name: 'Netzbezug', value: kpis.total_grid_import_kwh || 0, color: '#3b82f6' },
      ]
    : [];

  // Project status distribution
  const statusData = metrics
    ? [
        { name: 'Aktiv', value: metrics.active_projects, color: '#3b82f6' },
        { name: 'Abgeschlossen', value: metrics.completed_projects, color: '#10b981' },
        { name: 'Entwurf', value: metrics.draft_projects, color: '#94a3b8' },
      ]
    : [];

  const formatNumber = (n: number) =>
    n?.toLocaleString('de-DE', { maximumFractionDigits: 0 }) || '0';

  const formatCurrency = (n: number) =>
    n?.toLocaleString('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }) ||
    '0 €';

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Analytics</h1>
        <p className="text-slate-500 mt-1">Portfolio-Übersicht und Performance-Metriken</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Gesamt Projekte</p>
              <p className="text-3xl font-bold mt-1">{metrics?.total_projects || 0}</p>
              <p className="text-blue-200 text-xs mt-2">
                {metrics?.active_projects || 0} aktiv
              </p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <FileText className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-100 text-sm">PV-Kapazität</p>
              <p className="text-3xl font-bold mt-1">
                {formatNumber(metrics?.total_pv_capacity_kw || 0)}
              </p>
              <p className="text-amber-200 text-xs mt-2">kWp installiert</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <Sun className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-emerald-100 text-sm">Speicherkapazität</p>
              <p className="text-3xl font-bold mt-1">
                {formatNumber(metrics?.total_battery_capacity_kwh || 0)}
              </p>
              <p className="text-emerald-200 text-xs mt-2">kWh gesamt</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <Battery className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Jährliche Ersparnis</p>
              <p className="text-3xl font-bold mt-1">
                {formatCurrency(metrics?.total_annual_savings_eur || 0)}
              </p>
              <p className="text-purple-200 text-xs mt-2">über alle Projekte</p>
            </div>
            <div className="bg-white/20 p-3 rounded-lg">
              <Euro className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Performance Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-100 p-2 rounded-lg">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Ø Autarkie</p>
              <p className="text-xl font-bold text-slate-900">
                {kpis?.avg_autonomy_percent?.toFixed(1) || '—'}%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="bg-amber-100 p-2 rounded-lg">
              <Zap className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Ø Eigenverbrauch</p>
              <p className="text-xl font-bold text-slate-900">
                {kpis?.avg_self_consumption_percent?.toFixed(1) || '—'}%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <Clock className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Ø Amortisation</p>
              <p className="text-xl font-bold text-slate-900">
                {metrics?.avg_payback_years?.toFixed(1) || '—'} Jahre
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-2 rounded-lg">
              <Leaf className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">CO₂-Ersparnis</p>
              <p className="text-xl font-bold text-slate-900">
                {formatNumber(kpis?.total_co2_savings_kg || 0)} kg
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Monthly Trends */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Monatliche Entwicklung</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="colorPv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorBattery" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickFormatter={(value) => {
                    const [year, month] = value.split('-');
                    const monthNames = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
                    return monthNames[parseInt(month) - 1];
                  }}
                />
                <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    `${formatNumber(value)} ${name === 'total_pv_kw' ? 'kWp' : 'kWh'}`,
                    name === 'total_pv_kw' ? 'PV-Leistung' : 'Speicher',
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="total_pv_kw"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  fill="url(#colorPv)"
                  name="PV kWp"
                />
                <Area
                  type="monotone"
                  dataKey="total_battery_kwh"
                  stroke="#10b981"
                  strokeWidth={2}
                  fill="url(#colorBattery)"
                  name="Speicher kWh"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Project Status Distribution */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Projekt-Status</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }) =>
                    percent > 0 ? `${name} ${(percent * 100).toFixed(0)}%` : ''
                  }
                  labelLine={false}
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, name: string) => [value, name]}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4">
            {statusData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-slate-600">
                  {item.name} ({item.value})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Energy Distribution */}
      {kpis?.total_pv_generation_kwh > 0 && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Energieverteilung (Portfolio)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={energyData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)} MWh`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  width={120}
                />
                <Tooltip
                  formatter={(value: number) => [`${formatNumber(value)} kWh`, 'Energie']}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {energyData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Recent Projects Table */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Aktuelle Projekte</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-3 px-4 font-medium text-slate-600">Kunde</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">PV</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Speicher</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Autarkie</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Ersparnis/Jahr</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {dashboard?.recent_projects?.map((project: any) => (
                <tr key={project.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-3 px-4">
                    <div>
                      <p className="font-medium text-slate-900">{project.customer_name}</p>
                      {project.project_name && (
                        <p className="text-xs text-slate-500">{project.project_name}</p>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-700">{project.pv_kw} kWp</td>
                  <td className="py-3 px-4 text-slate-700">{project.battery_kwh} kWh</td>
                  <td className="py-3 px-4">
                    {project.autonomy_percent ? (
                      <span className="text-emerald-600 font-medium">
                        {project.autonomy_percent.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {project.annual_savings_eur ? (
                      <span className="text-blue-600 font-medium">
                        {formatCurrency(project.annual_savings_eur)}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`
                      px-2 py-1 rounded-full text-xs font-medium
                      ${
                        project.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-700'
                          : project.status === 'active'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-slate-100 text-slate-600'
                      }
                    `}
                    >
                      {project.status === 'completed'
                        ? 'Abgeschlossen'
                        : project.status === 'active'
                        ? 'Aktiv'
                        : 'Entwurf'}
                    </span>
                  </td>
                </tr>
              ))}
              {(!dashboard?.recent_projects || dashboard.recent_projects.length === 0) && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    Noch keine Projekte vorhanden
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Offer Stats */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <div className="flex items-center gap-4">
            <div className="bg-amber-100 p-4 rounded-xl">
              <Clock className="w-8 h-8 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Offene Angebote</p>
              <p className="text-3xl font-bold text-slate-900">
                {dashboard?.offers_pending || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <div className="flex items-center gap-4">
            <div className="bg-emerald-100 p-4 rounded-xl">
              <CheckCircle className="w-8 h-8 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Unterschriebene Angebote</p>
              <p className="text-3xl font-bold text-slate-900">
                {dashboard?.offers_signed || 0}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
