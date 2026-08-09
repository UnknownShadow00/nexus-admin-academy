import Link from 'next/link';
import type { ReactNode } from 'react';

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-amber-400/30 bg-amber-950/20">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="font-mono text-xs font-black uppercase tracking-[0.25em] text-amber-400">
              Admin
            </p>
            <Link className="text-lg font-black text-zinc-100" href="/admin">
              Nexus Admin — Scenario Builder
            </Link>
          </div>
          <Link
            className="rounded-sm border border-zinc-700 px-3 py-2 text-xs font-bold uppercase text-zinc-300 hover:bg-zinc-800"
            href="/"
          >
            Back to student app
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}
