import { PageLoading } from '@/components/layout/PageLoading';
import Image from 'next/image';

export default function RootLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg">
          <Image src="/auxilia-logo.svg" alt="Auxilia logo" width={24} height={24} className="h-6 w-6 object-contain" priority />
        </div>
        <p className="text-sm font-semibold text-slate-700">Loading Auxilia...</p>
      </div>
      <PageLoading />
    </div>
  );
}
