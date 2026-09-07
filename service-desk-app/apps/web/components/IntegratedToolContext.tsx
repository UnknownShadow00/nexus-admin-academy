'use client';

import type { Ticket } from '@service-desk/shared';
import Link from 'next/link';
import React, { createContext, useContext } from 'react';

export interface IntegratedToolContextValue {
  ticket: Ticket;
  attemptNumber?: number;
  returnDestination: string | null;
  onBack?: () => void;
}

export const IntegratedToolContext =
  createContext<IntegratedToolContextValue | null>(null);
export const useIntegratedTool = () => useContext(IntegratedToolContext);

export function ToolBackLink() {
  const context = useIntegratedTool();
  const className =
    'sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-bold text-accent';
  return context ? (
    <button className={className} onClick={context.onBack} type="button">
      Back to ticket {context.ticket.id}
    </button>
  ) : (
    <Link className={className} href="/">
      Dashboard
    </Link>
  );
}
