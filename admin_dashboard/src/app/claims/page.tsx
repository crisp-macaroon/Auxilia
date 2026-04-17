'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search, Filter, Download, CloudRain, Car, TrendingUp, AlertTriangle, Eye, CheckCircle, XCircle, Clock } from 'lucide-react';
import { approveClaim, getClaimDetails, getClaims, getClaimStats, rejectClaim, type ClaimDetailsResponse, type ClaimListItem, type ClaimStatsResponse } from '@/lib/api';
import { cn, formatCurrency, formatDateTime, getStatusBadgeClass } from '@/lib/utils';

const iconMap = { rain: CloudRain, traffic: Car, surge: TrendingUp, road_disruption: AlertTriangle };
const iconColorMap = { rain: 'text-blue-600 bg-blue-100', traffic: 'text-orange-600 bg-orange-100', surge: 'text-purple-600 bg-purple-100', road_disruption: 'text-red-600 bg-red-100' };

export default function ClaimsPage() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [stats, setStats] = useState<ClaimStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [selectedClaimDetails, setSelectedClaimDetails] = useState<ClaimDetailsResponse | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [claimsResult, statsResult] = await Promise.allSettled([getClaims(), getClaimStats()]);

        if (claimsResult.status === 'fulfilled') {
          setClaims(claimsResult.value);
        } else {
          setError('Unable to load claims right now.');
        }

        if (statsResult.status === 'fulfilled') {
          setStats(statsResult.value);
        }
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  useEffect(() => {
    if (!selectedClaimId) {
      setSelectedClaimDetails(null);
      return;
    }

    let active = true;
    setDetailsLoading(true);

    void getClaimDetails(selectedClaimId)
      .then((details) => {
        if (active) setSelectedClaimDetails(details);
      })
      .finally(() => {
        if (active) setDetailsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedClaimId]);

  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      const matchesStatus = statusFilter === 'all' || claim.status === statusFilter;
      const matchesSearch = claim.id.toLowerCase().includes(searchQuery.toLowerCase()) || claim.rider_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [claims, searchQuery, statusFilter]);

  async function handleApprove(claimId: string) {
    await approveClaim(claimId);
    const refreshed = await getClaims();
    setClaims(refreshed);
  }

  async function handleReject(claimId: string) {
    await rejectClaim(claimId);
    const refreshed = await getClaims();
    setClaims(refreshed);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Claims Management</h1>
          <p className="text-slate-500">Review and process insurance claims</p>
        </div>
        <button
          onClick={() => {
            const csv = 'Claim ID,Policy ID,Rider ID,Trigger Type,Trigger Value,Threshold,Amount,Fraud Score,Status,Created At\n' + claims.map((claim) => `${claim.id},${claim.policy_id},${claim.rider_id},${claim.trigger_type},${claim.trigger_value},${claim.threshold},${claim.amount},${claim.fraud_score},${claim.status},${claim.created_at}`).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'claims.csv';
            a.click();
            window.URL.revokeObjectURL(url);
          }}
          className="flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600"
        >
          <Download className="h-4 w-4" />Export Claims
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        {[
          { label: 'Total Claims', value: stats?.total_claims ?? 0, color: 'text-slate-900' },
          { label: 'Pending', value: stats?.pending_claims ?? 0, color: 'text-yellow-600' },
          { label: 'Approved', value: stats?.approved_claims ?? 0, color: 'text-green-600' },
          { label: 'Rejected', value: stats?.rejected_claims ?? 0, color: 'text-red-600' },
          { label: 'Payouts', value: formatCurrency(stats?.total_payout ?? 0), color: 'text-blue-600' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className={cn('text-2xl font-bold', stat.color)}>{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search by claim ID or rider ID..." className="w-full rounded-lg border border-slate-200 py-2 pl-10 pr-4 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20" />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500">
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="approved">Approved</option>
            <option value="paid">Paid</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            {[...Array.from({ length: 5 })].map((_, index) => (
              <div key={`claim-stat-skel-${index}`} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
            ))}
          </div>
          <div className="h-96 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
        </div>
      ) : null}

      {!loading ? <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {['Claim ID', 'Rider', 'Trigger', 'Amount', 'Fraud Score', 'Status', 'Time', 'Actions'].map((header) => (
                  <th key={header} className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading ? (
                <tr><td className="px-6 py-8 text-sm text-slate-500" colSpan={8}>Loading claims...</td></tr>
              ) : filteredClaims.map((claim) => {
                const Icon = iconMap[claim.trigger_type as keyof typeof iconMap] ?? AlertTriangle;
                const iconColors = iconColorMap[claim.trigger_type as keyof typeof iconColorMap] ?? 'text-slate-600 bg-slate-100';
                return (
                  <tr key={claim.id} className="transition-colors hover:bg-slate-50">
                    <td className="px-6 py-4"><div><span className="font-mono text-sm font-medium text-slate-900">{claim.id}</span><p className="text-xs text-slate-500">{claim.policy_id}</p></div></td>
                    <td className="px-6 py-4"><div><p className="text-sm font-medium text-slate-900">{claim.rider_id.slice(0, 8)}</p><p className="text-xs text-slate-500">Rider ID</p></div></td>
                    <td className="px-6 py-4"><div className="flex items-center gap-2"><div className={cn('rounded-lg p-1.5', iconColors.split(' ')[1])}><Icon className={cn('h-4 w-4', iconColors.split(' ')[0])} /></div><div><span className="text-sm capitalize text-slate-700">{claim.trigger_type}</span><p className="text-xs text-slate-500">{claim.trigger_value} / {claim.threshold}</p></div></div></td>
                    <td className="px-6 py-4"><span className="text-sm font-semibold text-slate-900">{formatCurrency(claim.amount)}</span></td>
                    <td className="px-6 py-4"><div className="flex items-center gap-2"><div className="h-2 w-16 rounded-full bg-slate-200"><div className={cn('h-2 rounded-full', claim.fraud_score < 0.3 ? 'bg-green-500' : claim.fraud_score < 0.6 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: `${claim.fraud_score * 100}%` }} /></div><span className="text-xs text-slate-500">{(claim.fraud_score * 100).toFixed(0)}%</span></div></td>
                    <td className="px-6 py-4"><span className={cn('inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize', getStatusBadgeClass(claim.status))}>{claim.status}</span></td>
                    <td className="px-6 py-4"><span className="text-sm text-slate-500">{formatDateTime(claim.created_at)}</span></td>
                      <td className="px-6 py-4"><div className="flex items-center gap-2"><button onClick={() => setSelectedClaimId(claim.id)} className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"><Eye className="h-4 w-4" /></button>{claim.status === 'pending' && <><button onClick={() => void handleApprove(claim.id)} className="rounded-lg p-2 text-green-500 transition-colors hover:bg-green-50"><CheckCircle className="h-4 w-4" /></button><button onClick={() => void handleReject(claim.id)} className="rounded-lg p-2 text-red-500 transition-colors hover:bg-red-50"><XCircle className="h-4 w-4" /></button></>}{claim.status === 'processing' && <button className="rounded-lg p-2 text-purple-500 transition-colors hover:bg-purple-50"><Clock className="h-4 w-4" /></button>}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div> : null}

      {selectedClaimId ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setSelectedClaimId(null)}>
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">Claim Details</h3>
            {(() => {
              const claim = claims.find((c) => c.id === selectedClaimId);
              if (detailsLoading) return <p className="mt-3 text-sm text-slate-500">Loading claim details...</p>;
              if (!claim) return <p className="mt-3 text-sm text-slate-500">Claim not found.</p>;

              const payoutDecision = selectedClaimDetails?.payout_decision;
              const earningContext = selectedClaimDetails?.earning_context;
              const rider = selectedClaimDetails?.rider;
              const zone = selectedClaimDetails?.zone;

              return (
                <div className="mt-4 space-y-2 text-sm text-slate-700">
                  <p><span className="font-medium text-slate-900">Claim ID:</span> {claim.id}</p>
                  <p><span className="font-medium text-slate-900">Policy ID:</span> {claim.policy_id}</p>
                  <p><span className="font-medium text-slate-900">Rider ID:</span> {claim.rider_id}</p>
                  <p><span className="font-medium text-slate-900">Zone:</span> {zone?.name ?? 'Unknown'}{zone?.city ? `, ${zone.city}` : ''}</p>
                  <p><span className="font-medium text-slate-900">Trigger:</span> {claim.trigger_type}</p>
                  <p><span className="font-medium text-slate-900">Amount:</span> {formatCurrency(claim.amount)}</p>
                  <p><span className="font-medium text-slate-900">Fraud score:</span> {(claim.fraud_score * 100).toFixed(0)}%</p>
                  <p><span className="font-medium text-slate-900">Status:</span> {claim.status}</p>
                  <p><span className="font-medium text-slate-900">Created:</span> {formatDateTime(claim.created_at)}</p>
                  {rider ? <p><span className="font-medium text-slate-900">Rider earning model:</span> {rider.earning_model?.replace('_', ' ')}</p> : null}
                  {payoutDecision ? <p><span className="font-medium text-slate-900">Payout exposure multiplier:</span> {payoutDecision.earning_exposure_multiplier.toFixed(2)}x</p> : null}
                  {earningContext ? <p><span className="font-medium text-slate-900">Zone earning index:</span> {earningContext.zone_earning_index.toFixed(2)}x</p> : null}
                  {earningContext ? <p><span className="font-medium text-slate-900">Rider earning factor:</span> {earningContext.rider_earning_factor.toFixed(2)}x</p> : null}
                  {rider?.avg_hourly_income ? <p><span className="font-medium text-slate-900">Avg hourly income:</span> {formatCurrency(rider.avg_hourly_income)}</p> : null}
                  {rider?.avg_order_value ? <p><span className="font-medium text-slate-900">Avg order value:</span> {formatCurrency(rider.avg_order_value)}</p> : null}
                </div>
              );
            })()}
            <div className="mt-6 flex justify-end">
              <button onClick={() => setSelectedClaimId(null)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
