'use client';

import { IconArrowLeft, IconUserCheck } from '@tabler/icons-react';
import Link from 'next/link';

import { ActivityTimeline } from './ActivityTimeline';
import { NotesSection } from './NotesSection';
import { RelatedDevicePanel } from './RelatedDevicePanel';
import { RequesterCard } from './RequesterCard';
import { SuggestedTools } from './SuggestedTools';
import { TicketActionBar } from './TicketActionBar';
import { TicketDetailHeader } from './TicketDetailHeader';
import { TicketIssueDetails } from './TicketIssueDetails';
import { useTicketSession } from './TicketSessionProvider';

export function TicketWorkspace({ ticketId }: { ticketId: string }) {
  const { addNote, getTicket } = useTicketSession();
  const ticket = getTicket(ticketId);

  if (!ticket) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center">
        <h1 className="text-xl font-bold text-zinc-100">
          Ticket fixture unavailable
        </h1>
        <p className="mt-2 text-sm text-zinc-400">
          Return to the queue and choose an active incident.
        </p>
        <Link
          className="sd-button sd-button--default sd-focus-ring mt-5 inline-flex min-h-10 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm font-extrabold uppercase text-zinc-200 hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          href="/"
        >
          Back to queue
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-4 sm:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          className="sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-semibold text-zinc-400 transition-colors hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          href="/"
        >
          <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
          Back to queue
        </Link>
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          <IconUserCheck aria-hidden="true" className="h-4 w-4 text-sky-400" />
          {ticket.assignedTo === 'you'
            ? 'Assigned to you'
            : 'Shared queue incident'}
        </span>
      </div>

      <TicketDetailHeader ticket={ticket} />
      <TicketActionBar ticket={ticket} />

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(18rem,0.85fr)]">
        <div className="min-w-0 space-y-4">
          <TicketIssueDetails description={ticket.description} />
          <NotesSection
            notes={ticket.notes}
            onAddNote={(body) => addNote(ticket.id, body)}
          />
        </div>
        <aside
          aria-label="Requester and related context"
          className="min-w-0 space-y-4"
        >
          <RequesterCard requester={ticket.requester} />
          <RelatedDevicePanel device={ticket.device} />
          <SuggestedTools
            ticketCategory={ticket.category}
            ticketId={ticket.id}
            toolSlugs={ticket.suggestedTools}
          />
        </aside>
      </div>

      <ActivityTimeline events={ticket.activity} />
    </div>
  );
}
