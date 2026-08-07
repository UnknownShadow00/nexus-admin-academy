'use client';

import { IconChevronRight, type Icon as TablerIcon } from '@tabler/icons-react';
import { Priority, type TicketCategory } from '@service-desk/shared';
import { Card, CardHeader, PriorityBadge } from '@service-desk/ui';

export interface DashboardTicket {
  category: TicketCategory;
  priority: Priority;
  requester: string;
  title: string;
}

interface DashboardQueueCardProps {
  icon: TablerIcon;
  label: string;
  meta: string;
  onSelectTicket: (ticket: DashboardTicket) => void;
  tickets: readonly DashboardTicket[];
}

export function DashboardQueueCard({
  icon: Icon,
  label,
  meta,
  onSelectTicket,
  tickets,
}: DashboardQueueCardProps) {
  return (
    <Card aria-label={label}>
      <CardHeader
        meta={meta}
        title={
          <span className="flex items-center gap-2">
            <Icon aria-hidden="true" className="h-5 w-5 text-sky-400" />
            {label}
          </span>
        }
      />
      <div className="divide-y divide-zinc-800">
        {tickets.map((ticket) => (
          <button
            aria-label={`Preview ticket: ${ticket.title}`}
            className="sd-focus-ring group flex w-full min-w-0 items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-zinc-800/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400"
            key={`${ticket.requester}-${ticket.title}`}
            onClick={() => onSelectTicket(ticket)}
            type="button"
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold leading-snug text-zinc-100 sm:text-base">
                {ticket.title}
              </span>
              <span className="mt-1 block text-xs font-semibold uppercase tracking-wide text-zinc-400 sm:text-sm">
                {ticket.requester}
              </span>
            </span>
            <PriorityBadge
              className="mt-0.5 shrink-0"
              priority={ticket.priority}
            />
            <IconChevronRight
              aria-hidden="true"
              className="mt-0.5 h-5 w-5 shrink-0 text-zinc-600 transition-colors group-hover:text-sky-400"
            />
          </button>
        ))}
      </div>
    </Card>
  );
}
