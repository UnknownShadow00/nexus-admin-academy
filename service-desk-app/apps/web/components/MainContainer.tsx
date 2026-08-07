'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

export function MainContainer({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const isRemoteDesktop = pathname === '/tools/remote-desktop';

  return (
    <main
      className={`mx-auto w-full flex-1 px-2 py-4 sm:px-4 md:px-8 md:py-6 ${isRemoteDesktop ? 'max-w-[1600px]' : 'max-w-7xl'}`}
    >
      {children}
    </main>
  );
}
