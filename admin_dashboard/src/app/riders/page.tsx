'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search, Filter, Download, UserPlus, Eye, MoreVertical, Phone, MapPin, Bike } from 'lucide-react';
import {
  getRider,
  getRiderClaims,
  getRiderPolicies,
  getRiders,
  getRiderStats,
  getZones,
  type RiderListItem,
  type RiderStatsResponse,
  type ClaimListItem,
  type PolicyListItem,
  type ZoneListItem,
  updateRider, createRider,
} from '@/lib/api';
import { cn, formatCurrency, formatDate, getStatusBadgeClass } from '@/lib/utils';

export default function RidersPage() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [riders, setRiders] = useState<RiderListItem[]>([]);
  const [stats, setStats] = useState<RiderStatsResponse | null>(null);
  const [activeMenuRiderId, setActiveMenuRiderId] = useState<string | null>(null);
  const [selectedRider, setSelectedRider] = useState<RiderListItem | null>(null);
  const [selectedPolicies, setSelectedPolicies] = useState<PolicyListItem[]>([]);
  const [selectedClaims, setSelectedClaims] = useState<ClaimListItem[]>([]);
  const [zones, setZones] = useState<ZoneListItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRider, setNewRider] = useState({ name: '', phone: '', persona: 'qcommerce' as const, zone_id: '' });


  async function reload() {
    const [items, overview] = await Promise.all([getRiders(), getRiderStats()]);
    setRiders(items);
    setStats(overview);
  }

  useEffect(() => {
    async function load() {
      const [items, overview, zoneItems] = await Promise.all([getRiders(), getRiderStats(), getZones({ is_active: true })]);
      setRiders(items);
      setStats(overview);
      setZones(zoneItems);
      if (zoneItems.length > 0) {
        setNewRider((current) => current.zone_id ? current : { ...current, zone_id: zoneItems[0].id });
      }
    }
    void load();
  }, []);

  const filteredRiders = useMemo(
    () =>
      riders.filter((rider) => {
        const matchesStatus = statusFilter === 'all' || rider.status === statusFilter;
        const query = searchQuery.toLowerCase();
        const matchesSearch = rider.name.toLowerCase().includes(query) || rider.phone.includes(searchQuery) || rider.id.toLowerCase().includes(query);
        return matchesStatus && matchesSearch;
      }),
    [riders, searchQuery, statusFilter]
  );

  const inactiveCount = riders.filter((item) => item.status === 'inactive').length;
  const suspendedCount = riders.filter((item) => item.status === 'suspended').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Rider Management</h1>
          <p className="text-slate-500">Manage registered delivery riders</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => {
            const csv = 'ID,Name,Phone,Persona,Risk Basis,Status,Risk\n' + riders.map(r => `${r.id},${r.name},${r.phone},${r.persona},delivery_path_dynamic,${r.status},${r.risk_score}`).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'riders.csv';
            a.click();
          }} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50">
            <Download className="h-4 w-4" /> Export
          </button>
          <button onClick={() => setShowAddModal(true)} className="flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
            <UserPlus className="h-4 w-4" /> Add Rider
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          { label: 'Total Riders', value: stats?.total_riders ?? 0, color: 'text-slate-900' },
          { label: 'Active', value: stats?.active_riders ?? 0, color: 'text-green-600' },
          { label: 'Inactive', value: inactiveCount, color: 'text-gray-600' },
          { label: 'Suspended', value: suspendedCount, color: 'text-red-600' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-4"><p className="text-sm text-slate-500">{stat.label}</p><p className={cn('text-2xl font-bold', stat.color)}>{stat.value}</p></div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input type="text" placeholder="Search by name, ID or phone..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full rounded-lg border border-slate-200 py-2 pl-10 pr-4 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20" /></div>
        <div className="flex items-center gap-2"><Filter className="h-4 w-4 text-slate-400" /><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500"><option value="all">All Status</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option></select></div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredRiders.map((rider) => {
          const avatar = rider.name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase();
          const menuOpen = activeMenuRiderId === rider.id;
          return (
            <div key={rider.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              <div className="flex items-start justify-between"><div className="flex items-center gap-4"><div className={cn('flex h-14 w-14 items-center justify-center rounded-full text-lg font-bold text-white', rider.persona === 'qcommerce' ? 'bg-gradient-to-br from-orange-500 to-orange-600' : 'bg-gradient-to-br from-purple-500 to-purple-600')}>{avatar}</div><div><h3 className="font-semibold text-slate-900">{rider.name}</h3><p className="text-sm text-slate-500">{rider.id}</p></div></div><span className={cn('inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize', getStatusBadgeClass(rider.status))}>{rider.status}</span></div>

              <div className="mt-4 space-y-2"><div className="flex items-center gap-2 text-sm text-slate-600"><Phone className="h-4 w-4 text-slate-400" />{rider.phone}</div><div className="flex items-center gap-2 text-sm text-slate-600"><MapPin className="h-4 w-4 text-slate-400" />Dynamic delivery path risk</div><div className="flex items-center gap-2 text-sm text-slate-600"><Bike className="h-4 w-4 text-slate-400" /><span className="capitalize">{rider.persona.replace('_', ' ')}</span></div></div>

              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4"><div className="text-center"><p className="text-lg font-bold text-slate-900">{(rider.risk_score * 100).toFixed(0)}%</p><p className="text-xs text-slate-500">Risk</p></div><div className="text-center"><p className="text-lg font-bold text-slate-900">{rider.status}</p><p className="text-xs text-slate-500">Status</p></div></div>
              <div className="mt-3"><div className="h-2 w-full rounded-full bg-slate-100"><div className={cn('h-2 rounded-full transition-all', rider.risk_score < 0.3 ? 'bg-green-500' : rider.risk_score < 0.6 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: `${rider.risk_score * 100}%` }} /></div></div>

              <div className="relative mt-4 flex items-center gap-2 border-t border-slate-100 pt-4">
                <button
                  onClick={async () => {
                    const [r, riderPolicies, riderClaims] = await Promise.all([getRider(rider.id), getRiderPolicies(rider.id), getRiderClaims(rider.id)]);
                    setSelectedRider(r);
                    setSelectedPolicies(riderPolicies.policies);
                    setSelectedClaims(riderClaims.claims);
                  }}
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <Eye className="mx-auto h-4 w-4" />
                </button>
                <button onClick={() => setActiveMenuRiderId(menuOpen ? null : rider.id)} className="rounded-lg border border-slate-200 px-3 py-2 text-slate-600 transition-colors hover:bg-slate-50"><MoreVertical className="h-4 w-4" /></button>
                {menuOpen ? (
                  <div className="absolute right-0 top-14 z-20 w-52 rounded-lg border border-slate-200 bg-white p-1 shadow-lg">
                    <button className="w-full rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100" onClick={async () => { const [r, riderPolicies, riderClaims] = await Promise.all([getRider(rider.id), getRiderPolicies(rider.id), getRiderClaims(rider.id)]); setSelectedRider(r); setSelectedPolicies(riderPolicies.policies); setSelectedClaims(riderClaims.claims); setActiveMenuRiderId(null); }}>
                      View profile
                    </button>
                    <button className="w-full rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50" onClick={async () => { await updateRider(rider.id, { status: 'suspended' }); await reload(); setActiveMenuRiderId(null); }}>
                      Suspend rider
                    </button>
                  </div>
                ) : null}
              </div>

            </div>
          );
        })}
      </div>

      {showAddModal ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setShowAddModal(false)}>
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">Add New Rider</h3>
            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
                <input type="text" value={newRider.name} onChange={e => setNewRider({...newRider, name: e.target.value})} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500" placeholder="John Doe" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Phone</label>
                <input type="text" value={newRider.phone} onChange={e => setNewRider({...newRider, phone: e.target.value})} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500" placeholder="+919876543210" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Persona</label>
                <select value={newRider.persona} onChange={e => setNewRider({...newRider, persona: e.target.value as any})} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500">
                  <option value="qcommerce">Q-Commerce</option>
                  <option value="food_delivery">Food Delivery</option>
                </select>
              </div>
              <div className="rounded-xl border border-orange-100 bg-orange-50 p-3 text-sm text-orange-900">
                Rider risk routing is delivery-driven. Auxilia will infer active risk from delivery destination and route path instead of manual zone assignment.
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setShowAddModal(false)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">Cancel</button>
              <button onClick={async () => {
                if (!newRider.name || !newRider.phone || !newRider.zone_id) return alert("Please fill all fields");
                await createRider(newRider);
                await reload();
                setShowAddModal(false);
                setNewRider({ name: '', phone: '', persona: 'qcommerce', zone_id: zones[0]?.id ?? '' });
              }} className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Save Rider</button>
            </div>
          </div>
        </div>
      ) : null}
      
      {selectedRider ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setSelectedRider(null)}>
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-900">Rider Profile</h3>
            <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700 md:grid-cols-2">
              <p><span className="font-medium text-slate-900">Name:</span> {selectedRider.name}</p>
              <p><span className="font-medium text-slate-900">Phone:</span> {selectedRider.phone}</p>
              <p><span className="font-medium text-slate-900">Risk Basis:</span> Delivery destination + path analysis</p>
              <p><span className="font-medium text-slate-900">Status:</span> {selectedRider.status}</p>
            </div>

            <div className="mt-4">
              <h4 className="text-sm font-semibold text-slate-900">Active / Recent Policies</h4>
              <div className="mt-2 max-h-36 overflow-y-auto rounded-md border border-slate-200">
                {selectedPolicies.length === 0 ? <p className="p-3 text-xs text-slate-500">No policies found.</p> : selectedPolicies.map((p) => <p key={p.id} className="border-b border-slate-100 p-3 text-xs text-slate-700">{p.id} - {p.status} - {formatCurrency(p.premium)}</p>)}
              </div>
            </div>

            <div className="mt-4">
              <h4 className="text-sm font-semibold text-slate-900">Recent Claims</h4>
              <div className="mt-2 max-h-36 overflow-y-auto rounded-md border border-slate-200">
                {selectedClaims.length === 0 ? <p className="p-3 text-xs text-slate-500">No claims found.</p> : selectedClaims.map((c) => <p key={c.id} className="border-b border-slate-100 p-3 text-xs text-slate-700">{c.id} - {c.status} - {formatCurrency(c.amount)} - {formatDate(c.created_at)}</p>)}
              </div>
            </div>

            <div className="mt-6 flex justify-end"><button onClick={() => setSelectedRider(null)} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">Close</button></div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
