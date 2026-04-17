'use client';

import { Loader2 } from 'lucide-react';

export function PageLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 text-slate-600">
        <Loader2 className="h-5 w-5 animate-spin text-orange-500" />
        <span className="text-sm font-medium">Loading page data...</span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {[...Array.from({ length: 4 })].map((_, index) => (
          <div key={`kpi-${index}`} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
        ))}
      </div>

      <div className="h-64 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
      <div className="h-72 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />
    </div>
  );
}
