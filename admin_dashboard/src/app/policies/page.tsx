'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search, Filter, Download, Plus, Eye, MoreVertical, Shield, Zap, Bike } from 'lucide-react';
import {
  cancelPolicy,
  createPolicy,
  getPolicies,
  getPolicyDetails,
  getPolicyStats,
  getRiders,
  getZones,
  renewPolicy,
  type PolicyListItem,
  type PolicyStatsResponse,
  type RiderListItem,
  type ZoneListItem,
  type PolicyDetailsResponse,
} from '@/lib/api';
import { cn, formatCurrency, formatDate, getStatusBadgeClass } from '@/lib/utils';

export default function PoliciesPage() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [policies, setPolicies] = useState<PolicyListItem[]>([]);
  const [stats, setStats] = useState<PolicyStatsResponse | null>(null);
  const [activeMenuPolicyId, setActiveMenuPolicyId] = useState<string | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyDetailsResponse | null>(null);
  const [showCreatePolicy, setShowCreatePolicy] = useState(false);
  const [riders, setRiders] = useState<RiderListItem[]>([]);
  const [zones, setZones] = useState<ZoneListItem[]>([]);
  const [createForm, setCreateForm] = useState({ rider_id: '', zone_id: '', persona: 'qcommerce' as 'qcommerce' | 'food_delivery', duration_days: 7 });  // Weekly default
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function reload() {
    setError(null);
    const [policiesResult, statsResult] = await Promise.allSettled([getPolicies(), getPolicyStats()]);

    if (policiesResult.status === 'fulfilled') {
      setPolicies(policiesResult.value);
    } else {
      setError('Unable to load policies right now.');
    }

    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value);
    }
  }

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const [policiesResult, statsResult, ridersResult, zonesResult] = await Promise.allSettled([
        getPolicies(),
        getPolicyStats(),
        getRiders(),
        getZones({ is_active: true }),
      ]);

      if (policiesResult.status === 'fulfilled') {
        setPolicies(policiesResult.value);
      } else {
        setError('Some policy data failed to load. Please refresh.');
      }

      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value);
      }

      if (ridersResult.status === 'fulfilled') {
        setRiders(ridersResult.value);
      }

      if (zonesResult.status === 'fulfilled') {
        setZones(zonesResult.value);
      }

      setLoading(false);
    }
    void load();
  }, []);

  const filteredPolicies = useMemo(
    () =>
      policies.filter((policy) => {
        const matchesStatus = statusFilter === 'all' || policy.status === statusFilter;
        const query = searchQuery.toLowerCase();
        const matchesSearch = policy.id.toLowerCase().includes(query) || policy.rider_id.toLowerCase().includes(query);
        return matchesStatus && matchesSearch;
      }),
    [policies, searchQuery, statusFilter]
  );

  const personaCounts = policies.reduce((acc, policy) => {
    acc[policy.persona] = (acc[policy.persona] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Policy Management</h1>
          <p className="text-slate-500">Manage all rider insurance policies</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => {
            const csv = 'ID,Rider ID,Zone ID,Persona,Premium,Coverage,Start Date,End Date,Status\n' + policies.map(p => `${p.id},${p.rider_id},${p.zone_id},${p.persona},${p.premium},${p.coverage},${p.start_date},${p.end_date},${p.status}`).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'policies.csv';
            a.click();
          }} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50">
            <Download className="h-4 w-4" /> Export
          </button>
          <button onClick={() => setShowCreatePolicy(true)} className="flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
            <Plus className="h-4 w-4" /> New Policy
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          { label: 'Total Policies', value: stats?.total_policies ?? 0, icon: Shield, color: 'text-blue-600', bg: 'bg-blue-100' },
          { label: 'Active Policies', value: stats?.active_policies ?? 0, icon: Zap, color: 'text-green-600', bg: 'bg-green-100' },
          { label: 'Q-Commerce', value: personaCounts.qcommerce ?? 0, icon: Bike, color: 'text-orange-600', bg: 'bg-orange-100' },
          { label: 'Food Delivery', value: personaCounts.food_delivery ?? 0, icon: Bike, color: 'text-purple-600', bg: 'bg-purple-100' },
        ].map((stat) => (
          <div key={stat.label} className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
            <div className={cn('rounded-xl p-3', stat.bg)}>
              <stat.icon className={cn('h-6 w-6', stat.color)} />
            </div>
            <div>
              <p className="text-sm text-slate-500">{stat.label}</p>
              <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input type="text" placeholder="Search by policy ID or rider ID..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full rounded-lg border border-slate-200 py-2 pl-10 pr-4 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20" />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500">
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            {[...Array.from({ length: 4 })].map((_, index) => (
              <div key={`policy-stat-skel-${index}`} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
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
                {['Policy ID', 'Rider', 'Persona / Zone', 'Premium', 'Coverage', 'Validity', 'Status', 'Actions'].map((header) => (
                  <th key={header} className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filteredPolicies.map((policy) => {
                const menuOpen = activeMenuPolicyId === policy.id;
                return (
                  <tr key={policy.id} className="transition-colors hover:bg-slate-50">
                    <td className="px-6 py-4"><span className="font-mono text-sm font-medium text-slate-900">{policy.id}</span></td>
                    <td className="px-6 py-4"><div><p className="text-sm font-medium text-slate-900">{policy.rider_id.slice(0, 8)}</p><p className="text-xs text-slate-500">Rider ID</p></div></td>
                    <td className="px-6 py-4"><div><span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize', policy.persona === 'qcommerce' ? 'bg-orange-100 text-orange-700' : 'bg-purple-100 text-purple-700')}>{policy.persona.replace('_', ' ')}</span><p className="mt-1 text-xs text-slate-500">{policy.zone_id}</p></div></td>
                    <td className="px-6 py-4"><span className="text-sm font-semibold text-slate-900">{formatCurrency(policy.premium)}/wk</span></td>
                    <td className="px-6 py-4"><span className="text-sm text-slate-700">{formatCurrency(policy.coverage)}</span></td>
                    <td className="px-6 py-4"><div><p className="text-sm text-slate-700">{formatDate(policy.start_date)}</p><p className="text-xs text-slate-500">to {formatDate(policy.end_date)}</p></div></td>
                    <td className="px-6 py-4"><span className={cn('inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize', getStatusBadgeClass(policy.status))}>{policy.status}</span></td>
                    <td className="px-6 py-4">
                      <div className="relative flex items-center gap-2">
                        <button
                          onClick={async () => {
                            const details = await getPolicyDetails(policy.id);
                            setSelectedPolicy(details);
                          }}
                          className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button onClick={() => setActiveMenuPolicyId(menuOpen ? null : policy.id)} className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600">
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {menuOpen ? (
                          <div className="absolute right-0 top-10 z-20 w-44 rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
                            <button className="w-full rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100" onClick={async () => { const details = await getPolicyDetails(policy.id); setSelectedPolicy(details); setActiveMenuPolicyId(null); }}>
                              Edit policy
                            </button>
                            <button className="w-full rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100" onClick={async () => { await renewPolicy(policy.id, 7); await reload(); setActiveMenuPolicyId(null); }}>
                              Extend 1 week
                            </button>
                            <button className="w-full rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50" onClick={async () => { await cancelPolicy(policy.id); await reload(); setActiveMenuPolicyId(null); }}>
                              Cancel policy
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div> : null}

      {selectedPolicy ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setSelectedPolicy(null)}>
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">Policy Details</h3>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              <p><span className="font-medium text-slate-900">Policy ID:</span> {selectedPolicy.policy.id}</p>
              <p><span className="font-medium text-slate-900">Rider ID:</span> {selectedPolicy.policy.rider_id}</p>
              <p><span className="font-medium text-slate-900">Zone:</span> {selectedPolicy.zone?.name ?? selectedPolicy.policy.zone_id}</p>
              <p><span className="font-medium text-slate-900">Premium:</span> {formatCurrency(selectedPolicy.policy.premium)}</p>
              <p><span className="font-medium text-slate-900">Coverage:</span> {formatCurrency(selectedPolicy.policy.coverage)}</p>
              <p><span className="font-medium text-slate-900">Status:</span> {selectedPolicy.policy.status}</p>
              <p><span className="font-medium text-slate-900">Days Remaining:</span> {selectedPolicy.days_remaining}</p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setSelectedPolicy(null)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">Close</button>
            </div>
          </div>
        </div>
      ) : null}

      {showCreatePolicy ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setShowCreatePolicy(false)}>
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">Create New Policy</h3>
            <div className="mt-4 grid grid-cols-1 gap-3">
              <select value={createForm.rider_id} onChange={(e) => setCreateForm((p) => ({ ...p, rider_id: e.target.value }))} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="">Select rider</option>
                {riders.map((r) => <option key={r.id} value={r.id}>{r.name} ({r.id.slice(0, 8)})</option>)}
              </select>
              <select value={createForm.zone_id} onChange={(e) => setCreateForm((p) => ({ ...p, zone_id: e.target.value }))} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="">Select zone</option>
                {zones.map((z) => <option key={z.id} value={z.id}>{z.name} ({z.city})</option>)}
              </select>
              <select value={createForm.persona} onChange={(e) => setCreateForm((p) => ({ ...p, persona: e.target.value as 'qcommerce' | 'food_delivery' }))} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="qcommerce">Q-Commerce</option>
                <option value="food_delivery">Food Delivery</option>
              </select>
              <input type="number" min={7} max={56} step={7} placeholder="Duration (weeks: 7, 14, 21...)" value={createForm.duration_days} onChange={(e) => setCreateForm((p) => ({ ...p, duration_days: Number(e.target.value) }))} className="rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setShowCreatePolicy(false)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">Cancel</button>
              <button
                onClick={async () => {
                  if (!createForm.rider_id || !createForm.zone_id) return;
                  await createPolicy(createForm);
                  await reload();
                  setShowCreatePolicy(false);
                }}
                className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
