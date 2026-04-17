'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  ClipboardList,
  Users,
  BarChart3,
  Zap,
  Settings,
  Shield,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Policies', href: '/policies', icon: FileText },
  { name: 'Claims', href: '/claims', icon: ClipboardList },
  { name: 'Riders', href: '/riders', icon: Users },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Triggers', href: '/triggers', icon: Zap },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
    router.refresh();
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r border-slate-200 bg-white text-slate-900 transition-all duration-300',
        isCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg">
            <Shield className="h-6 w-6 text-white" />
          </div>
          {!isCollapsed && (
            <span className="text-xl font-bold tracking-tight text-slate-900">Auxilia</span>
          )}
        </Link>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="rounded-lg p-2 hover:bg-slate-100 lg:block"
        >
          {isCollapsed ? <Menu className="h-5 w-5 text-slate-600" /> : <X className="h-5 w-5 text-slate-600" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-6 flex flex-col gap-1 px-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-orange-50 text-orange-600 shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              )}
            >
              <item.icon className={cn('h-5 w-5', isActive && 'text-orange-600')} />
              {!isCollapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-slate-200 p-4">
        <div className={cn('flex items-center gap-3', isCollapsed && 'justify-center')}>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-teal-600 text-sm font-bold">
            AD
          </div>
          {!isCollapsed && (
            <div className="flex-1">
              <p className="text-sm font-medium">Admin User</p>
              <p className="text-xs text-slate-500">admin@auxilia.in</p>
            </div>
          )}
          {!isCollapsed && (
            <button className="rounded-lg p-2 hover:bg-slate-100" onClick={handleLogout}>
              <LogOut className="h-4 w-4 text-slate-500" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
