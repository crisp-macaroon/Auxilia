'use client';

import { useState } from 'react';
import { Save, Bell, Shield, Database, Wallet, Globe, Key } from 'lucide-react';
import { cn } from '@/lib/utils';

const settingsSections = [
  { id: 'general', name: 'General', icon: Globe },
  { id: 'notifications', name: 'Notifications', icon: Bell },
  { id: 'security', name: 'Security', icon: Shield },
  { id: 'blockchain', name: 'Blockchain', icon: Wallet },
  { id: 'api', name: 'API Keys', icon: Key },
  { id: 'data', name: 'Data & Export', icon: Database },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState('general');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500">Manage your platform configuration</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 shrink-0">
          <nav className="space-y-1">
            {settingsSections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all',
                  activeSection === section.id
                    ? 'bg-orange-50 text-orange-600'
                    : 'text-slate-600 hover:bg-slate-50'
                )}
              >
                <section.icon className="h-5 w-5" />
                {section.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeSection === 'general' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-lg font-semibold text-slate-900">General Settings</h3>
              <p className="text-sm text-slate-500">Basic platform configuration</p>

              <div className="mt-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Platform Name
                  </label>
                  <input
                    type="text"
                    defaultValue="Auxilia Insurance"
                    className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Default Currency
                  </label>
                  <select className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-orange-500">
                    <option>INR - Indian Rupee</option>
                    <option>USD - US Dollar</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Default Timezone
                  </label>
                  <select className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-orange-500">
                    <option>Asia/Kolkata (IST)</option>
                    <option>UTC</option>
                  </select>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
                  <div>
                    <p className="font-medium text-slate-900">Auto-approve Low Risk Claims</p>
                    <p className="text-sm text-slate-500">
                      Automatically approve claims with fraud score below 0.3
                    </p>
                  </div>
                  <button
                    className="relative h-6 w-11 rounded-full bg-orange-500 transition-colors"
                  >
                    <span className="absolute right-1 top-1 h-4 w-4 rounded-full bg-white shadow" />
                  </button>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
                  <div>
                    <p className="font-medium text-slate-900">Real-time Trigger Monitoring</p>
                    <p className="text-sm text-slate-500">
                      Enable live data feeds for parametric triggers
                    </p>
                  </div>
                  <button
                    className="relative h-6 w-11 rounded-full bg-orange-500 transition-colors"
                  >
                    <span className="absolute right-1 top-1 h-4 w-4 rounded-full bg-white shadow" />
                  </button>
                </div>
              </div>

              <div className="mt-8 flex justify-end">
                <button className="flex items-center gap-2 rounded-xl bg-orange-500 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {activeSection === 'blockchain' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-lg font-semibold text-slate-900">Blockchain Settings</h3>
              <p className="text-sm text-slate-500">Configure blockchain integration</p>

              <div className="mt-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Network
                  </label>
                  <select className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-orange-500">
                    <option>Polygon Mumbai (Testnet)</option>
                    <option>Polygon Mainnet</option>
                    <option>Ethereum Sepolia (Testnet)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Contract Address
                  </label>
                  <input
                    type="text"
                    defaultValue="0x1234567890abcdef1234567890abcdef12345678"
                    className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 font-mono text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    RPC URL
                  </label>
                  <input
                    type="text"
                    defaultValue="https://rpc-mumbai.maticvigil.com"
                    className="mt-2 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
                  />
                </div>

                <div className="rounded-lg bg-green-50 p-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-green-500" />
                    <span className="text-sm font-medium text-green-700">
                      Contract Connected
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-green-600">
                    ClaimLedger contract is active and responding
                  </p>
                </div>
              </div>

              <div className="mt-8 flex justify-end">
                <button className="flex items-center gap-2 rounded-xl bg-orange-500 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-lg font-semibold text-slate-900">Notification Settings</h3>
              <p className="text-sm text-slate-500">Configure alerts and notifications</p>

              <div className="mt-6 space-y-4">
                {[
                  { label: 'New claim submitted', description: 'Get notified when a new claim is submitted' },
                  { label: 'Claim approved/rejected', description: 'Get notified when a claim status changes' },
                  { label: 'Trigger activated', description: 'Get notified when a parametric trigger activates' },
                  { label: 'High fraud score', description: 'Get notified when a claim has high fraud probability' },
                  { label: 'Policy expired', description: 'Get notified when policies expire' },
                ].map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4"
                  >
                    <div>
                      <p className="font-medium text-slate-900">{item.label}</p>
                      <p className="text-sm text-slate-500">{item.description}</p>
                    </div>
                    <button
                      className={cn(
                        'relative h-6 w-11 rounded-full transition-colors',
                        index < 3 ? 'bg-orange-500' : 'bg-slate-200'
                      )}
                    >
                      <span
                        className={cn(
                          'absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all',
                          index < 3 ? 'right-1' : 'left-1'
                        )}
                      />
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex justify-end">
                <button className="flex items-center gap-2 rounded-xl bg-orange-500 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-orange-600">
                  <Save className="h-4 w-4" />
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {(activeSection === 'security' || activeSection === 'api' || activeSection === 'data') && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-lg font-semibold text-slate-900 capitalize">
                {activeSection} Settings
              </h3>
              <p className="text-sm text-slate-500">
                Configure {activeSection} options
              </p>
              <div className="mt-12 text-center">
                <p className="text-slate-400">Settings panel coming soon...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
