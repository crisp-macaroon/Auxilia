'use client';

import { usePathname } from 'next/navigation';

import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';
  const isGatewayPage = pathname === '/';

  if (isLoginPage || isGatewayPage) {
    return <main className="min-h-screen w-full bg-white">{children}</main>;
  }

  return (
    <div className="flex min-h-screen w-full bg-white">
      <Sidebar />
      <div className="ml-64 flex-1 bg-white transition-all duration-300">
        <Header />
        <main className="min-h-[calc(100vh-4rem)] bg-white p-6">{children}</main>
      </div>
    </div>
  );
}
