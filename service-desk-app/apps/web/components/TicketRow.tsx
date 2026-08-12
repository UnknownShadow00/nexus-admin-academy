import {
  FIXTURE_REFERENCE_TIME,
  formatDueIndicator,
  formatRelativeTime,
  type Ticket,
} from '@service-desk/shared';
import { PriorityBadge } from '@service-desk/ui';
import {
  IconChevronRight,
  IconClock,
  IconHourglassHigh,
} from '@tabler/icons-react';
import Link from 'next/link';

import { TicketStatusBadge } from './TicketStatusBadge';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

export function TicketRow({
  assignment,
  ticket,
}: {
  assignment?: NexusAssignment;
  ticket: Ticket;
}) {
  const dueLabel = formatDueIndicator(ticket.sla.dueAt, FIXTURE_REFERENCE_TIME);
  const urgent = dueLabel === 'SLA overdue' || dueLabel.startsWith('Due in 0');

  return (
    <Link
      aria-label={`Open ticket ${ticket.id}: ${ticket.title}`}
      className="sd-focus-ring group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2 px-3 py-3 transition-colors hover:bg-zinc-800/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 sm:grid-cols-[8rem_minmax(0,1fr)_10rem_8rem_1.25rem] sm:items-center sm:px-4"
      href={`/tickets/${ticket.id}`}
    >
      <span className="col-start-1 row-start-2 flex items-center gap-2 sm:col-start-1 sm:row-start-1 sm:flex-col sm:items-start">
        <PriorityBadge priority={ticket.priority} />
        {assignment?.difficulty_label ? (
          <span className="whitespace-nowrap text-[11px] font-semibold text-zinc-500">
            <span aria-hidden="true" className="text-amber-400">
              {assignment.difficulty_stars}
            </span>{' '}
            {assignment.difficulty_label}
          </span>
        ) : null}
      </span>
      <span className="col-start-1 row-start-1 min-w-0 sm:col-start-2">
        <span className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 font-mono text-xs font-semibold text-sky-400">
            {ticket.id}
          </span>
          <span className="truncate text-sm font-bold leading-snug text-zinc-100 sm:text-base">
            {ticket.title}
          </span>
        </span>
        <span className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-400">
          <span className="inline-flex items-center gap-1 whitespace-nowrap">
            <IconClock aria-hidden="true" className="h-3.5 w-3.5" />
            {formatRelativeTime(ticket.createdAt, FIXTURE_REFERENCE_TIME)}
          </span>
          <span aria-hidden="true" className="text-zinc-700">
            ·
          </span>
          <span
            className={`inline-flex items-center gap-1 whitespace-nowrap font-semibold ${
              urgent ? 'text-red-400' : 'text-zinc-400'
            }`}
          >
            <IconHourglassHigh aria-hidden="true" className="h-3.5 w-3.5" />
            {dueLabel}
          </span>
        </span>
      </span>
      <span className="hidden min-w-0 truncate text-sm font-semibold text-zinc-300 sm:col-start-3 sm:block">
        {ticket.requester.name}
      </span>
      <span className="col-start-2 row-start-2 flex items-center justify-end sm:col-start-4 sm:row-start-1 sm:justify-start">
        <TicketStatusBadge status={ticket.status} />
      </span>
      <IconChevronRight
        aria-hidden="true"
        className="col-start-2 row-start-1 h-5 w-5 self-center justify-self-end text-zinc-600 transition-colors group-hover:text-sky-400 sm:col-start-5"
      />
    </Link>
  );
}
