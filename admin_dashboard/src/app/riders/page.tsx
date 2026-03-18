'use client';

import { useState } from 'react';
import { Search, Filter, Download, UserPlus, Eye, MoreVertical, Phone, MapPin, Bike } from 'lucide-react';
import { cn, formatDate, getStatusBadgeClass } from '@/lib/utils';

const riders = [
  {
    id: 'RDR-1847',
    name: 'Rahul Sharma',
    phone: '+91 98765 43210',
    email: 'rahul.sharma@email.com',
    persona: 'qcommerce',
    zone: 'Andheri',
    riskScore: 0.45,
    totalClaims: 8,
    totalPolicies: 3,
    joinedAt: '2025-08-15',
    status: 'active',
    avatar: 'RS',
  },
  {
    id: 'RDR-1846',
    name: 'Priya Patel',
    phone: '+91 98765 43211',
    email: 'priya.patel@email.com',
    persona: 'food_delivery',
    zone: 'Dadar',
    riskScore: 0.32,
    totalClaims: 4,
    totalPolicies: 2,
    joinedAt: '2025-10-22',
    status: 'active',
    avatar: 'PP',
  },
  {
    id: 'RDR-1845',
    name: 'Amit Kumar',
    phone: '+91 98765 43212',
    email: 'amit.kumar@email.com',
    persona: 'qcommerce',
    zone: 'Bandra',
    riskScore: 0.58,
    totalClaims: 15,
    totalPolicies: 5,
    joinedAt: '2025-05-10',
    status: 'active',
    avatar: 'AK',
  },
  {
    id: 'RDR-1844',
    name: 'Sneha Desai',
    phone: '+91 98765 43213',
    email: 'sneha.desai@email.com',
    persona: 'food_delivery',
    zone: 'Kurla',
    riskScore: 0.25,
    totalClaims: 2,
    totalPolicies: 1,
    joinedAt: '2026-01-05',
    status: 'active',
    avatar: 'SD',
  },
  {
    id: 'RDR-1843',
    name: 'Vikram Singh',
    phone: '+91 98765 43214',
    email: 'vikram.singh@email.com',
    persona: 'qcommerce',
    zone: 'Powai',
    riskScore: 0.72,
    totalClaims: 22,
    totalPolicies: 6,
    joinedAt: '2025-03-18',
    status: 'suspended',
    avatar: 'VS',
  },
  {
    id: 'RDR-1842',
    name: 'Neha Gupta',
    phone: '+91 98765 43215',
    email: 'neha.gupta@email.com',
    persona: 'food_delivery',
    zone: 'Malad',
    riskScore: 0.38,
    totalClaims: 6,
    totalPolicies: 2,
    joinedAt: '2025-11-30',
    status: 'inactive',
    avatar: 'NG',
  },
];

export default function RidersPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredRiders = riders.filter((rider) => {
    const matchesStatus = statusFilter === 'all' || rider.status === statusFilter;
    const matchesSearch =
      rider.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rider.phone.includes(searchQuery);
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Rider Management</h1>
          <p className="text-slate-500">Manage registered delivery riders</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50">
            <Download className="h-4 w-4" />
            Export
          </button>
          <button className="flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
            <UserPlus className="h-4 w-4" />
            Add Rider
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          { label: 'Total Riders', value: '1,234', color: 'text-slate-900' },
          { label: 'Active', value: '1,089', color: 'text-green-600' },
          { label: 'Inactive', value: '98', color: 'text-gray-600' },
          { label: 'Suspended', value: '47', color: 'text-red-600' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className={cn('text-2xl font-bold', stat.color)}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, ID or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-200 py-2 pl-10 pr-4 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      {/* Riders Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredRiders.map((rider) => (
          <div
            key={rider.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    'flex h-14 w-14 items-center justify-center rounded-full text-lg font-bold text-white',
                    rider.persona === 'qcommerce'
                      ? 'bg-gradient-to-br from-orange-500 to-orange-600'
                      : 'bg-gradient-to-br from-purple-500 to-purple-600'
                  )}
                >
                  {rider.avatar}
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">{rider.name}</h3>
                  <p className="text-sm text-slate-500">{rider.id}</p>
                </div>
              </div>
              <span
                className={cn(
                  'inline-flex rounded-full border px-2.5 py-1 text-xs font-medium capitalize',
                  getStatusBadgeClass(rider.status)
                )}
              >
                {rider.status}
              </span>
            </div>

            {/* Info */}
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <Phone className="h-4 w-4 text-slate-400" />
                {rider.phone}
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <MapPin className="h-4 w-4 text-slate-400" />
                {rider.zone}
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <Bike className="h-4 w-4 text-slate-400" />
                <span className="capitalize">{rider.persona.replace('_', ' ')}</span>
              </div>
            </div>

            {/* Stats */}
            <div className="mt-4 grid grid-cols-3 gap-4 border-t border-slate-100 pt-4">
              <div className="text-center">
                <p className="text-lg font-bold text-slate-900">{rider.totalPolicies}</p>
                <p className="text-xs text-slate-500">Policies</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-slate-900">{rider.totalClaims}</p>
                <p className="text-xs text-slate-500">Claims</p>
              </div>
              <div className="text-center">
                <p
                  className={cn(
                    'text-lg font-bold',
                    rider.riskScore < 0.3
                      ? 'text-green-600'
                      : rider.riskScore < 0.6
                      ? 'text-yellow-600'
                      : 'text-red-600'
                  )}
                >
                  {(rider.riskScore * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-slate-500">Risk</p>
              </div>
            </div>

            {/* Risk Bar */}
            <div className="mt-3">
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div
                  className={cn(
                    'h-2 rounded-full transition-all',
                    rider.riskScore < 0.3
                      ? 'bg-green-500'
                      : rider.riskScore < 0.6
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  )}
                  style={{ width: `${rider.riskScore * 100}%` }}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
              <p className="text-xs text-slate-500">Joined {formatDate(rider.joinedAt)}</p>
              <div className="flex items-center gap-2">
                <button className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600">
                  <Eye className="h-4 w-4" />
                </button>
                <button className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600">
                  <MoreVertical className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-6 py-4">
        <p className="text-sm text-slate-500">
          Showing <span className="font-medium">1-6</span> of{' '}
          <span className="font-medium">1,234</span> riders
        </p>
        <div className="flex items-center gap-2">
          <button className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
            Previous
          </button>
          <button className="rounded-lg bg-orange-500 px-3 py-1.5 text-sm font-medium text-white">
            1
          </button>
          <button className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
            2
          </button>
          <button className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
