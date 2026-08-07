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

export function TicketRow({ ticket }: { ticket: Ticket }) {
  const dueLabel = formatDueIndicator(ticket.sla.dueAt, FIXTURE_REFERENCE_TIME);
  const urgent = dueLabel === 'SLA overdue' || dueLabel.startsWith('Due in 0');

  return (
    <Link
      aria-label={`Open ticket ${ticket.id}: ${ticket.title}`}
      className="sd-focus-ring group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2 px-3 py-3 transition-colors hover:bg-zinc-800/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center sm:px-4"
      href={`/tickets/${ticket.id}`}
    >
      <span className="col-start-1 row-start-1 min-w-0">
        <span className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 font-mono text-xs font-semibold text-sky-400">
            {ticket.id}
          </span>
          <span className="truncate text-sm font-bold leading-snug text-zinc-100 sm:text-base">
            {ticket.title}
          </span>
        </span>
        <span className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-400">
          <span className="font-semibold">{ticket.requester.name}</span>
          <span aria-hidden="true" className="text-zinc-700">
            ·
          </span>
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
      <span className="col-start-1 row-start-2 flex items-center justify-start gap-2 sm:col-start-2 sm:row-start-1 sm:justify-end">
        <PriorityBadge priority={ticket.priority} />
        <TicketStatusBadge status={ticket.status} />
      </span>
      <IconChevronRight
        aria-hidden="true"
        className="col-start-2 row-start-1 h-5 w-5 self-center justify-self-end text-zinc-600 transition-colors group-hover:text-sky-400 sm:col-start-3"
      />
    </Link>
  );
}
