import type { Ticket } from '@service-desk/shared';
import { PriorityBadge } from '@service-desk/ui';
import { IconChevronRight } from '@tabler/icons-react';
import Link from 'next/link';
import React from 'react';

import { TicketStatusBadge } from './TicketStatusBadge';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

const MODE_LABELS: Record<NexusAssignment['experience_mode'], string> = {
  assessment: 'Independent assessment',
  guided: 'Guided practice',
  practice: 'Practice',
};

export function TicketRow({
  assignment,
  ticket,
}: {
  assignment?: NexusAssignment;
  ticket: Ticket;
}) {
  return (
    <Link
      aria-label={`Open ticket ${ticket.id}: ${ticket.title}`}
      className="sd-focus-ring group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2 px-3 py-3 transition-colors hover:bg-surface-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus sm:grid-cols-[8rem_minmax(0,1fr)_10rem_8rem_1.25rem] sm:items-center sm:px-4"
      href={`/tickets/${ticket.id}`}
    >
      <span className="col-start-1 row-start-2 flex items-center gap-2 sm:col-start-1 sm:row-start-1">
        <PriorityBadge priority={ticket.priority} />
      </span>
      <span className="col-start-1 row-start-1 min-w-0 sm:col-start-2">
        <span className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 font-mono text-xs font-semibold text-accent">
            {ticket.id}
          </span>
          <span className="truncate text-sm font-bold leading-snug text-text sm:text-base">
            {ticket.title}
          </span>
        </span>
        <span className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-muted">
          {assignment ? (
            <span className="font-bold uppercase tracking-wide text-accent">
              {MODE_LABELS[assignment.experience_mode]}
            </span>
          ) : null}
          {assignment?.required_this_week ? (
            <span className="font-semibold text-warning">
              Required this week
            </span>
          ) : null}
        </span>
      </span>
      <span className="hidden min-w-0 truncate text-sm font-semibold text-text sm:col-start-3 sm:block">
        {ticket.requester.name}
      </span>
      <span className="col-start-2 row-start-2 flex items-center justify-end sm:col-start-4 sm:row-start-1 sm:justify-start">
        <TicketStatusBadge status={ticket.status} />
      </span>
      <IconChevronRight
        aria-hidden="true"
        className="col-start-2 row-start-1 h-5 w-5 self-center justify-self-end text-text-muted transition-colors group-hover:text-accent sm:col-start-5"
      />
    </Link>
  );
}
