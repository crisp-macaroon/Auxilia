'use client';

import { useEffect, useMemo, useState } from 'react';
import { CloudRain, Car, TrendingUp, AlertTriangle, Settings, RefreshCw } from 'lucide-react';

import { cn } from '@/lib/utils';
import { getTriggerStatus, triggerRefresh, type TriggerStatusResponse } from '@/lib/api';

const iconMap = {
  rain: CloudRain,
  traffic: Car,
  surge: TrendingUp,
  road_disruption: AlertTriangle,
};

const colorMap = {
  rain: {
    bg: 'bg-blue-100',
    text: 'text-blue-600',
    border: 'border-blue-200',
    gradient: 'from-blue-500 to-blue-600',
    light: 'bg-blue-50',
  },
  traffic: {
    bg: 'bg-orange-100',
    text: 'text-orange-600',
    border: 'border-orange-200',
    gradient: 'from-orange-500 to-orange-600',
    light: 'bg-orange-50',
  },
  surge: {
    bg: 'bg-violet-100',
    text: 'text-violet-600',
    border: 'border-violet-200',
    gradient: 'from-violet-500 to-violet-600',
    light: 'bg-violet-50',
  },
  road_disruption: {
    bg: 'bg-red-100',
    text: 'text-red-600',
    border: 'border-red-200',
    gradient: 'from-red-500 to-red-600',
    light: 'bg-red-50',
  },
};

type GroupedTrigger = {
  type: string;
  zones: Array<{
    name: string;
    current: number;
    threshold: number;
    isActive: boolean;
    affected: number;
  }>;
  lastUpdated: string;
};

export default function TriggersPage() {
  const [data, setData] = useState<TriggerStatusResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function load() {
    setData(await getTriggerStatus());
  }

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      await triggerRefresh();
      await load();
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const triggerGroups = useMemo<GroupedTrigger[]>(() => {
    const groups: Record<string, GroupedTrigger> = {};
    const zones = data?.zones ?? {};

    Object.values(zones).forEach((zone) => {
      zone.triggers.forEach((trigger) => {
        if (!groups[trigger.trigger_type]) {
          groups[trigger.trigger_type] = {
            type: trigger.trigger_type,
            zones: [],
            lastUpdated: trigger.last_updated,
          };
        }

        groups[trigger.trigger_type].zones.push({
          name: trigger.zone_name,
          current: trigger.current_value,
          threshold: trigger.threshold,
          isActive: trigger.is_active,
          affected: trigger.affected_policies,
        });

        groups[trigger.trigger_type].lastUpdated = trigger.last_updated;
      });
    });

    return Object.values(groups);
  }, [data]);

  const hasGroups = triggerGroups.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Trigger Management</h1>
          <p className="text-slate-500">Monitor and configure parametric triggers</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => void handleRefresh()}
            disabled={isRefreshing}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            {isRefreshing ? 'Refreshing...' : 'Refresh All'}
          </button>
        </div>
      </div>

      {hasGroups ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {triggerGroups.map((trigger) => {
              const colors = colorMap[trigger.type as keyof typeof colorMap] ?? colorMap.road_disruption;
              const activeZones = trigger.zones.filter((zone) => zone.isActive);
              const totalAffected = activeZones.reduce((sum, zone) => sum + zone.affected, 0);
              const Icon = iconMap[trigger.type as keyof typeof iconMap] ?? AlertTriangle;

              return (
                <div
                  key={trigger.type}
                  className={cn(
                    'rounded-xl border-2 p-4 transition-all',
                    activeZones.length > 0 ? `${colors.border} ${colors.light}` : 'border-slate-200 bg-white'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn('rounded-xl p-2.5', colors.bg)}>
                        <Icon className={cn('h-5 w-5', colors.text)} />
                      </div>
                      <div>
                        <p className="font-semibold capitalize text-slate-900">{trigger.type}</p>
                        <p className="text-xs text-slate-500">{new Date(trigger.lastUpdated).toLocaleTimeString()}</p>
                      </div>
                    </div>
                    {activeZones.length > 0 ? (
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                        {activeZones.length}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-3">
                    {activeZones.length > 0 ? (
                      <p className={cn('text-sm font-medium', colors.text)}>{totalAffected} policies affected</p>
                    ) : (
                      <p className="text-sm text-slate-500">No active triggers</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="space-y-6">
            {triggerGroups.map((trigger) => {
              const colors = colorMap[trigger.type as keyof typeof colorMap] ?? colorMap.road_disruption;
              const Icon = iconMap[trigger.type as keyof typeof iconMap] ?? AlertTriangle;

              return (
                <div key={trigger.type} className="rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-6">
                    <div className="flex items-center gap-4">
                      <div className={cn('flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white', colors.gradient)}>
                        <Icon className="h-6 w-6" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold capitalize text-slate-900">{trigger.type} trigger</h3>
                        <p className="text-sm text-slate-500">Live threshold evaluation across zones</p>
                      </div>
                    </div>
                    <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                      <Settings className="h-5 w-5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-2 xl:grid-cols-3">
                    {trigger.zones.map((zone) => {
                      const percentage = Math.min((zone.current / Math.max(zone.threshold, 1)) * 100, 100);

                      return (
                        <div
                          key={`${trigger.type}-${zone.name}`}
                          className={cn(
                            'rounded-xl border p-4 transition-all',
                            zone.isActive ? `${colors.border} ${colors.light}` : 'border-slate-100 bg-slate-50/50'
                          )}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-medium text-slate-900">{zone.name}</p>
                            {zone.isActive ? <span className="flex h-2 w-2 animate-pulse rounded-full bg-red-500" /> : null}
                          </div>

                          <div className="mt-3">
                            <div className="flex items-baseline justify-between">
                              <p className={cn('text-2xl font-bold', zone.isActive ? colors.text : 'text-slate-600')}>
                                {zone.current}
                                <span className="text-sm font-normal text-slate-400">/{zone.threshold}</span>
                              </p>
                            </div>

                            <div className="mt-2">
                              <div className="h-2 w-full rounded-full bg-slate-200">
                                <div
                                  className={cn('h-2 rounded-full transition-all', zone.isActive ? 'bg-red-500' : colors.text.replace('text', 'bg'))}
                                  style={{ width: `${percentage}%` }}
                                />
                              </div>
                            </div>

                            <p className="mt-2 text-xs text-slate-500">{zone.affected} policies affected</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
          No trigger data available yet. Run a trigger refresh to fetch live conditions.
        </div>
      )}
    </div>
  );
}
