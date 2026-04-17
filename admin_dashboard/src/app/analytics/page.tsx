import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn, formatCurrency } from '@/lib/utils';
import { getArchitecture, getClaimsChart, getDashboardStats, getPersonaBreakdown, getRevenueMetrics, getTriggerDistribution, getZoneHeatmap, getZoneStats } from '@/lib/api';
import { ZoneHeatmap, ZoneMap } from '@/components/dashboard';

export default async function AnalyticsPage() {
  const [revenue, distribution, zones, stats, claimsChart, personas, heatmap, architecture] = await Promise.all([
    getRevenueMetrics(),
    getTriggerDistribution(),
    getZoneStats(),
    getDashboardStats(),
    getClaimsChart(),
    getPersonaBreakdown(),
    getZoneHeatmap(),
    getArchitecture(),
  ]);

  const monthlyData = claimsChart.data.map((item) => ({
    month: item.date ? new Date(item.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : 'N/A',
    claims: item.total,
    payouts: item.approved * (revenue.average_claim || 0),
  }));

  const chartSeries = monthlyData.slice(-8);
  const maxClaims = Math.max(...chartSeries.map((item) => item.claims), 1);
  const maxTriggerCount = Math.max(...distribution.distribution.map((item) => item.count), 1);
  const visibleZones = zones.zones
    .filter((zone) => zone.total_claims > 0 || zone.active_policies > 0 || zone.active_triggers > 0)
    .slice(0, 10);
  const totalPersonas = personas.personas.reduce((sum, persona) => sum + persona.count, 0);

  const kpis = [
    { label: 'Total Premium', value: formatCurrency(revenue.premium_collected), change: `${stats.active_policies} active`, trend: 'up' },
    { label: 'Total Payouts', value: formatCurrency(revenue.claims_paid), change: `${stats.total_claims} claims`, trend: 'up' },
    { label: 'Loss Ratio', value: `${revenue.loss_ratio.toFixed(1)}%`, change: 'Live backend metric', trend: revenue.loss_ratio > 80 ? 'up' : 'down' },
    { label: 'Avg Claim', value: formatCurrency(revenue.average_claim), change: 'Approved payouts only', trend: 'neutral' },
    { label: 'Fraud Detection', value: `${(1 - stats.avg_risk_score).toFixed(2)}`, change: 'Portfolio confidence', trend: 'up' },
    { label: 'Active Triggers', value: `${stats.active_triggers}`, change: 'Live trigger count', trend: 'neutral' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-slate-500">Dynamic risk architecture and flow</p>
        </div>
        <span className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700">Last 30 Days</span>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium text-slate-500">{kpi.label}</p>
              <p className="mt-1 text-xl font-bold text-slate-900">{kpi.value}</p>
              <div className="mt-2 flex items-center gap-1">
                {kpi.trend === 'up' ? <TrendingUp className="h-3 w-3 text-green-500" /> : kpi.trend === 'down' ? <TrendingDown className="h-3 w-3 text-red-500" /> : <Minus className="h-3 w-3 text-slate-400" />}
                <span className={cn('text-xs font-medium', kpi.trend === 'up' ? 'text-green-600' : kpi.trend === 'down' ? 'text-red-600' : 'text-slate-500')}>{kpi.change}</span>
              </div>
            </div>
          ))}
      </div>

      <ZoneHeatmap points={heatmap.points} />
      <ZoneMap points={heatmap.points} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-slate-900">Claims Trend</h3>
          <p className="text-sm text-slate-500">Recent claim volume from the backend</p>
          {chartSeries.length > 0 ? (
            <div className="mt-6 space-y-3">
              {chartSeries.map((item) => (
                <div key={item.month}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-slate-600">{item.month}</span>
                    <span className="font-medium text-slate-900">{item.claims} claims</span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-slate-100">
                    <div className="h-3 rounded-full bg-orange-500" style={{ width: `${(item.claims / maxClaims) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No claim trend data available yet.</div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-slate-900">Trigger Distribution</h3>
          <p className="text-sm text-slate-500">Claims by trigger type</p>
          {distribution.distribution.length > 0 ? (
            <div className="mt-6 space-y-3">
              {distribution.distribution.map((item) => (
                <div key={item.trigger_type}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="capitalize text-slate-700">{item.trigger_type}</span>
                    <span className="font-medium text-slate-900">{item.count}</span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-slate-100">
                    <div className="h-3 rounded-full bg-teal-500" style={{ width: `${(item.count / maxTriggerCount) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No trigger distribution data available yet.</div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">System Architecture & Pipeline</h3>
        <p className="text-sm text-slate-500">Updated flow for delivery-location risk and dynamic insurer zones</p>

        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-5">
          {Object.entries(architecture.architecture).map(([layer, items]) => (
            <div key={layer} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm font-semibold capitalize text-slate-900">{layer}</p>
              <ul className="mt-2 space-y-1 text-xs text-slate-600">
                {items.map((item) => <li key={item}>- {item}</li>)}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-xl border border-slate-100 bg-white p-4">
          <p className="text-sm font-semibold text-slate-900">Flow Chart</p>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            {architecture.pipeline.map((step, index) => (
              <div key={step} className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700">
                <span className="mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-200 px-1.5 text-[10px] font-semibold text-slate-700">
                  {index + 1}
                </span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/60 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">Zone Performance</h4>
                <p className="text-xs text-slate-500">Claims intensity across active delivery corridors</p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
                {visibleZones.length} zones
              </span>
            </div>
            {visibleZones.length > 0 ? (
              <div className="mt-4 space-y-4">
                {visibleZones.map((zone) => (
                  <div key={zone.zone_id} className="rounded-xl border border-white bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700">{zone.name}</span>
                      <span className="text-slate-500">{zone.total_claims} claims</span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="rounded bg-slate-100 px-2 py-0.5">Risk {((zone.current_risk ?? 0) * 100).toFixed(0)}%</span>
                      <span className="rounded bg-slate-100 px-2 py-0.5 capitalize">{zone.risk_level ?? 'medium'}</span>
                      {zone.event_window_seconds ? <span className="rounded bg-slate-100 px-2 py-0.5">{Math.round(zone.event_window_seconds / 60)}m window</span> : null}
                      {zone.risk_scope ? <span className="rounded bg-slate-100 px-2 py-0.5">{zone.risk_scope.replace('_', ' ')}</span> : null}
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-orange-500"
                        style={{ width: `${(zone.total_claims / Math.max(...visibleZones.map((item) => item.total_claims), 1)) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No zone performance data yet.</div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/60 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">Persona Mix</h4>
                <p className="text-xs text-slate-500">Current distribution of covered delivery workers</p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
                {totalPersonas} riders
              </span>
            </div>
            {personas.personas.length > 0 ? (
              <div className="mt-4 space-y-4">
                {personas.personas.map((persona) => (
                  <div key={persona.persona} className="rounded-xl border border-white bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium capitalize text-slate-700">{persona.persona.replace('_', ' ')}</span>
                      <span className="text-slate-900">{persona.count}</span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded-full bg-slate-100">
                      <div className="h-2 rounded-full bg-violet-500" style={{ width: `${(persona.count / Math.max(totalPersonas, 1)) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No persona data available yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
