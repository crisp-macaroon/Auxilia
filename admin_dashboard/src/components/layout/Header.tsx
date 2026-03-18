'use client';

import { Bell, Search, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export function Header() {
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications = [
    { id: 1, message: 'New claim submitted - Rain trigger in Andheri', time: '2 min ago', type: 'claim' },
    { id: 2, message: 'Policy #POL-2847 expired', time: '15 min ago', type: 'policy' },
    { id: 3, message: 'Traffic surge detected in Dadar zone', time: '32 min ago', type: 'trigger' },
  ];

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
      {/* Search */}
      <div className="relative w-96">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search policies, claims, riders..."
          className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none transition-all focus:border-orange-500 focus:bg-white focus:ring-2 focus:ring-orange-500/20"
        />
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        {/* Live Status */}
        <div className="flex items-center gap-2 rounded-full bg-green-50 px-4 py-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
          <span className="text-sm font-medium text-green-700">System Live</span>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-xl bg-slate-100 p-2.5 transition-colors hover:bg-slate-200"
          >
            <Bell className="h-5 w-5 text-slate-600" />
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-xs font-bold text-white">
              3
            </span>
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl">
              <div className="border-b border-slate-100 p-4">
                <h3 className="font-semibold text-slate-900">Notifications</h3>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className="border-b border-slate-50 p-4 transition-colors hover:bg-slate-50"
                  >
                    <p className="text-sm text-slate-700">{notif.message}</p>
                    <p className="mt-1 text-xs text-slate-400">{notif.time}</p>
                  </div>
                ))}
              </div>
              <div className="p-3">
                <button className="w-full rounded-lg bg-slate-100 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">
                  View All
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Date/Time */}
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="font-medium">
            {new Date().toLocaleDateString('en-IN', {
              weekday: 'short',
              day: 'numeric',
              month: 'short',
            })}
          </span>
          <ChevronDown className="h-4 w-4" />
        </div>
      </div>
    </header>
  );
}
