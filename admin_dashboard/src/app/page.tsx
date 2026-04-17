import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, Bike, UserCog } from 'lucide-react';

export default function RoleGatewayPage() {
  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(249,115,22,0.16),_transparent_42%),linear-gradient(120deg,#fff7ed_0%,#ffffff_58%,#ecfeff_100%)] px-6 py-10">
      <div className="absolute -left-24 top-6 h-72 w-72 rounded-full bg-orange-200/35 blur-3xl" />
      <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-cyan-200/35 blur-3xl" />

      <div className="relative mx-auto max-w-5xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg">
            <Image src="/auxilia-logo.svg" alt="Auxilia logo" width={28} height={28} className="h-7 w-7 object-contain" priority />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-500">Auxilia</p>
            <h1 className="text-3xl font-semibold text-slate-900">Choose your entry</h1>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-white/70 bg-white/90 p-7 shadow-xl backdrop-blur">
            <div className="mb-4 flex items-center gap-3">
              <span className="inline-flex rounded-xl bg-orange-50 p-3 text-orange-600">
                <Bike className="h-6 w-6" />
              </span>
              <span className="inline-flex rounded-xl border border-orange-100 bg-white p-2">
                <Image src="/auxilia-logo.svg" alt="Auxilia rider app logo" width={30} height={30} className="h-7 w-7 object-contain" />
              </span>
            </div>
            <h2 className="text-xl font-semibold text-slate-900">I am a rider</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use the Auxilia Rider App for onboarding, policy activation, route risk tracking, and claim visibility.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a
                href="https://github.com/crisp-macaroon/Auxilia/releases"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-2xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
              >
                Download Rider APK <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="https://github.com/crisp-macaroon/Auxilia/releases"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                View release notes
              </a>
            </div>
          </div>

          <div className="rounded-3xl border border-white/70 bg-white/90 p-7 shadow-xl backdrop-blur">
            <div className="mb-4 inline-flex rounded-xl bg-cyan-50 p-3 text-cyan-700">
              <UserCog className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">I am admin / operations</h2>
            <p className="mt-2 text-sm text-slate-600">
              Continue to the dashboard for rider monitoring, triggers, claims processing, and payout operations.
            </p>
            <div className="mt-6">
              <Link
                href="/login"
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Continue to admin login <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
