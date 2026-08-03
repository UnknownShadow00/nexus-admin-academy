'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { Footer } from './Footer';
import { Header } from './Header';
import { MainContainer } from './MainContainer';
import { TicketSessionProvider } from './TicketSessionProvider';

export function ApplicationShell({
  children,
}: Readonly<{ children: ReactNode }>) {
  const currentPath = usePathname();

  return (
    <TicketSessionProvider>
      <div className="flex min-h-screen w-full max-w-full flex-col overflow-x-hidden bg-zinc-950 text-zinc-100">
        <Header currentPath={currentPath} />
        <MainContainer>{children}</MainContainer>
        <Footer />
      </div>
    </TicketSessionProvider>
  );
}
