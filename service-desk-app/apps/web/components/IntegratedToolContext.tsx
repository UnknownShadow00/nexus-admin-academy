'use client';

import {
  getToolBySlug,
  type Ticket,
  type ToolSlug,
} from '@service-desk/shared';
import Link from 'next/link';
import React, { createContext, useContext } from 'react';
import type { ToolSelectionHandler } from './SuggestedTools';

export interface IntegratedToolContextValue {
  ticket: Ticket;
  ticketId?: string;
  assignmentId?: string | number;
  attemptId?: string | number;
  experienceMode?: 'guided' | 'practice' | 'assessment';
  attemptNumber?: number;
  returnDestination: string | null;
  onBack?: () => void;
  onSelectTool?: ToolSelectionHandler;
}

export const IntegratedToolContext =
  createContext<IntegratedToolContextValue | null>(null);
export const useIntegratedTool = () => useContext(IntegratedToolContext);

/** Existing cross-tool links become workspace actions only inside a ticket. */
export function IntegratedToolLink(props: React.ComponentProps<typeof Link>) {
  const context = useIntegratedTool();
  const href = typeof props.href === 'string' ? props.href : '';
  const [path, query] = href.split('?');
  const slug = path?.startsWith('/tools/') ? path.slice('/tools/'.length) : '';
  if (context?.onSelectTool && getToolBySlug(slug)) {
    return (
      <button
        className={props.className}
        onClick={() =>
          context.onSelectTool?.(slug as ToolSlug, new URLSearchParams(query))
        }
        type="button"
      >
        {props.children}
      </button>
    );
  }
  return <Link {...props} />;
}

export function ToolBackLink() {
  const context = useIntegratedTool();
  const className =
    'sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-bold text-accent';
  // The persistent pane owns the single integrated back control.
  return context ? null : (
    <Link className={className} href="/">
      Dashboard
    </Link>
  );
}
