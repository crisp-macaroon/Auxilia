import {
  FileText,
  ClipboardList,
  Users,
  IndianRupee,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { StatCard, ClaimsChart, LiveTriggers, RecentClaims, ZoneDistribution, ZoneHeatmap, ZoneMap } from '@/components/dashboard';
import {
  getClaimsChart,
  getDashboardStats,
  getLiveTriggers,
  getRecentClaims,
  getZoneHeatmap,
  getZoneStats,
} from '@/lib/api';
import { ADMIN_TOKEN_COOKIE, hasAdminToken } from '@/lib/auth';
import { formatCurrency } from '@/lib/utils';

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const adminToken = cookieStore.get(ADMIN_TOKEN_COOKIE)?.value;

  if (!hasAdminToken(adminToken)) {
    redirect('/login');
  }

  const [stats, claimsChart, recentClaims, liveTriggers, zoneStats, zoneHeatmap] = await Promise.all([
    getDashboardStats(),
    getClaimsChart(),
    getRecentClaims(8),
    getLiveTriggers(),
    getZoneStats(),
    getZoneHeatmap(),
  ]);

  const chartData = claimsChart.data.map((item) => ({
    name: item.date ? new Date(item.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : 'N/A',
    claims: item.total,
    approved: item.approved,
    rejected: item.rejected,
  }));

  const zoneData = zoneStats.zones
    .filter((zone) => zone.active_policies > 0 || zone.total_claims > 0 || zone.total_payouts > 0)
    .map((zone) => ({
      name: zone.name,
      value: zone.active_policies,
      risk: zone.risk_level === 'very_high' ? 'high' : zone.risk_level === 'high' ? 'high' : zone.risk_level === 'low' ? 'low' : 'medium',
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500">Live platform metrics from the Auxilia backend.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Policies" value={String(stats.active_policies)} change={`${stats.total_policies} total policies`} changeType="positive" icon={FileText} iconColor="text-blue-600" iconBg="bg-blue-100" />
        <StatCard title="Total Claims" value={String(stats.total_claims)} change={`${stats.pending_claims} pending review`} changeType="positive" icon={ClipboardList} iconColor="text-orange-600" iconBg="bg-orange-100" />
        <StatCard title="Active Riders" value={String(stats.active_riders)} change={`Avg risk ${stats.avg_risk_score.toFixed(2)}`} changeType="positive" icon={Users} iconColor="text-teal-600" iconBg="bg-teal-100" />
        <StatCard title="Premium Collected" value={formatCurrency(stats.total_premium_collected)} change={`Loss ratio ${stats.loss_ratio.toFixed(1)}%`} changeType="positive" icon={IndianRupee} iconColor="text-green-600" iconBg="bg-green-100" />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Claims Paid" value={formatCurrency(stats.total_claims_paid)} change="Approved payout volume" changeType="neutral" icon={TrendingUp} iconColor="text-purple-600" iconBg="bg-purple-100" />
        <StatCard title="Pending Claims" value={String(stats.pending_claims)} change="Needs processing" changeType="neutral" icon={ClipboardList} iconColor="text-yellow-600" iconBg="bg-yellow-100" />
        <StatCard title="Active Triggers" value={String(stats.active_triggers)} change={stats.active_triggers > 0 ? 'Live alerts in monitored zones' : 'No live alerts'} changeType={stats.active_triggers > 0 ? 'negative' : 'neutral'} icon={AlertTriangle} iconColor="text-red-600" iconBg="bg-red-100" />
        <StatCard title="Avg Risk Score" value={stats.avg_risk_score.toFixed(2)} change="Portfolio-wide rider risk" changeType="neutral" icon={TrendingUp} iconColor="text-slate-600" iconBg="bg-slate-100" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ClaimsChart data={chartData} />
        </div>
        <div>
          <ZoneDistribution data={zoneData} />
        </div>
      </div>

      <ZoneHeatmap points={zoneHeatmap.points} />
      <ZoneMap points={zoneHeatmap.points} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecentClaims
            claims={recentClaims.claims.map((claim) => ({
              id: claim.id,
              rider: claim.rider_name,
              type: claim.trigger_type,
              amount: claim.amount,
              status: claim.status,
              time: claim.created_at,
              zone: claim.zone_id,
            }))}
          />
        </div>
        <div>
          <LiveTriggers
            triggers={liveTriggers.triggers.map((trigger) => ({
              zone: trigger.zone_name,
              type: trigger.trigger_type,
              current: trigger.current_value,
              threshold: trigger.threshold,
              isActive: trigger.current_value >= trigger.threshold,
            }))}
          />
        </div>
      </div>
    </div>
  );
}
