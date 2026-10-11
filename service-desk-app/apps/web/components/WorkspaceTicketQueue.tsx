import type { Ticket } from '@service-desk/shared';
import { PriorityBadge } from '@service-desk/ui';
import Link from 'next/link';
import React from 'react';

import type { NexusAssignment } from '../lib/nexus-service-desk-client';
import { workspaceHref } from '../lib/workspace-navigation';
import { TicketStatusBadge } from './TicketStatusBadge';

type WorkspaceTicketQueueProps = {
  assignmentByTicket: Readonly<Record<string, NexusAssignment>>;
  launchQuery?: string;
  selectedTicketId: string;
  tickets: readonly Ticket[];
};

const QUEUE_GROUPS = [
  { key: 'assigned', label: 'Assigned' },
  { key: 'practice', label: 'Practice' },
  { key: 'earlier', label: 'Earlier' },
] as const;

function QueueTicketLink({
  href,
  selected,
  ticket,
}: {
  href: string;
  selected: boolean;
  ticket: Ticket;
}) {
  return (
    <Link
      aria-current={selected ? 'page' : undefined}
      aria-label={`${ticket.id}: ${ticket.title}`}
      className={`sd-focus-ring block min-w-0 border-l-[3px] px-3 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${
        selected
          ? 'border-accent bg-accent/10'
          : 'border-transparent hover:bg-surface-muted/50'
      }`}
      href={href}
    >
      <span className="flex min-w-0 items-center justify-between gap-2">
        <span className="font-mono text-xs font-bold text-text-muted">
          {ticket.id}
        </span>
        <PriorityBadge priority={ticket.priority} />
      </span>
      <span className="mt-1 block break-words text-sm font-semibold leading-snug text-text">
        {ticket.title}
      </span>
      <span className="mt-2 flex min-w-0 items-center justify-between gap-2 text-xs text-text-muted">
        <span className="min-w-0 truncate">{ticket.requester.name}</span>
        <TicketStatusBadge status={ticket.status} />
      </span>
    </Link>
  );
}

export function WorkspaceTicketQueue({
  assignmentByTicket,
  launchQuery = '',
  selectedTicketId,
  tickets,
}: WorkspaceTicketQueueProps) {
  const selectedTicket = tickets.find(
    (ticket) => ticket.id === selectedTicketId,
  );
  return (
    <nav
      aria-label="Ticket queue"
      className="sd-ticket-queue sticky top-4 hidden min-w-0 self-start overflow-hidden rounded-md border border-border bg-surface-raised lg:block"
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-bold text-text">Tickets</h2>
        <Link
          className="sd-focus-ring rounded-sm text-xs font-semibold text-accent underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          href={workspaceHref('/', launchQuery, selectedTicketId)}
        >
          View queue
        </Link>
      </div>
      {selectedTicket ? (
        <section aria-label="Current ticket" className="border-b border-border">
          <h3 className="bg-surface px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-text-muted">
            Current ticket
          </h3>
          <QueueTicketLink
            href={workspaceHref(
              `/tickets/${selectedTicket.id}`,
              launchQuery,
              selectedTicketId,
            )}
            selected
            ticket={selectedTicket}
          />
        </section>
      ) : null}
      <div className="max-h-[calc(100dvh-11rem)] overflow-y-auto">
        {QUEUE_GROUPS.map(({ key, label }) => {
          const groupTickets = tickets.filter(
            (ticket) =>
              ticket.id !== selectedTicketId &&
              (assignmentByTicket[ticket.id]?.queue_type ?? 'assigned') === key,
          );
          if (groupTickets.length === 0) return null;
          return (
            <section aria-label={label} key={key}>
              <h3 className="border-b border-border bg-surface px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-text-muted">
                {label}
              </h3>
              <ul className="divide-y divide-border">
                {groupTickets.map((ticket) => (
                  <li key={ticket.id}>
                    <QueueTicketLink
                      href={workspaceHref(
                        `/tickets/${ticket.id}`,
                        launchQuery,
                        selectedTicketId,
                      )}
                      selected={false}
                      ticket={ticket}
                    />
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
        {tickets.length === 0 ? (
          <p className="px-4 py-6 text-sm text-text-muted">
            No tickets available.
          </p>
        ) : null}
      </div>
    </nav>
  );
}
