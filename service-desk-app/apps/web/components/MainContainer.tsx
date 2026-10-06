'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

export function MainContainer({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const isRemoteDesktop = pathname === '/tools/remote-desktop';
  const isServiceDesk = pathname === '/' || pathname.startsWith('/tickets/');

  return (
    <main
      className={`mx-auto w-full min-w-0 flex-1 px-3 py-4 sm:px-5 md:px-6 md:py-6 ${isRemoteDesktop || isServiceDesk ? 'max-w-[1600px]' : 'max-w-7xl'}`}
    >
      {children}
    </main>
  );
}
