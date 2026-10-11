'use client';

import type { ReactNode } from 'react';

import { AcademyFrame } from './AcademyFrame';
import { TicketSessionProvider } from './TicketSessionProvider';

export function ApplicationShell({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <TicketSessionProvider>
      <AcademyFrame>{children}</AcademyFrame>
    </TicketSessionProvider>
  );
}
