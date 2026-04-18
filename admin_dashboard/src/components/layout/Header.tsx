'use client';

import { Bell, Search, ChevronDown } from 'lucide-react';
import { useMemo, useState, useEffect } from 'react';
import { getLiveTriggers, getPricingAlerts, getRecentClaims } from '@/lib/api';

type NotificationItem = {
  id: string;
  message: string;
  time: string;
  type: 'trigger' | 'claim' | 'pricing';
};

type TriggerNotification = Awaited<ReturnType<typeof getLiveTriggers>>['triggers'][number];
type ClaimNotification = Awaited<ReturnType<typeof getRecentClaims>>['claims'][number];
type PricingNotification = Awaited<ReturnType<typeof getPricingAlerts>>['alerts'][number];


export function Header() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const currentDateLabel = useMemo(
    () =>
      new Date().toLocaleDateString('en-IN', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
      }),
    []
  );

  useEffect(() => {
    async function loadNotifications() {
      try {
        const [triggersRes, claimsRes, pricingRes] = await Promise.all([
          getLiveTriggers(),
          getRecentClaims(5),
          getPricingAlerts(),
        ]);

        const newNotifs: NotificationItem[] = [];
        
        triggersRes.triggers.forEach((t: TriggerNotification, i: number) => {
          newNotifs.push({
            id: `trigger-${i}`,
            message: `${t.trigger_type.toUpperCase()} alert in ${t.zone_name}`,
            time: new Date(t.last_updated).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
            type: 'trigger'
          });
        });

        claimsRes.claims.forEach((c: ClaimNotification, i: number) => {
          newNotifs.push({
            id: `claim-${i}`,
            message: `New claim (${c.trigger_type}) - ${c.status}`,
            time: new Date(c.created_at).toLocaleDateString(),
            type: 'claim'
          });
        });

        pricingRes.alerts.forEach((alert: PricingNotification, i: number) => {
          const direction = alert.weekly_adjustment > 0 ? 'up' : 'down';
          newNotifs.push({
            id: `pricing-${i}`,
            message: `Weekly premium ${direction} to Rs ${alert.suggested_weekly_premium} in ${alert.zone_name} (${alert.pricing_note})`,
            time: new Date(alert.assessed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            type: 'pricing',
          });
        });

        setNotifications(newNotifs.slice(0, 12));
        setUnreadCount(newNotifs.length);
      } catch (e) {
        console.error("Failed to load notifications", e);
      }
    }
    
    void loadNotifications();
    const interval = setInterval(loadNotifications, 60000);
    return () => clearInterval(interval);
  }, []);


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
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-xl bg-slate-100 p-2.5 transition-colors hover:bg-slate-200"
          >
            <Bell className="h-5 w-5 text-slate-600" />
                        {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-xs font-bold text-white">
                {unreadCount}
              </span>
            )}
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
          <span className="font-medium">{currentDateLabel || 'Auxilia Admin'}</span>
          <ChevronDown className="h-4 w-4" />
        </div>
      </div>
    </header>
  );
}
