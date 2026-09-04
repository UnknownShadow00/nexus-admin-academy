'use client';

import type { Ticket } from '@service-desk/shared';

import { EscalateDialog } from './EscalateDialog';
import { ResolveDialog } from './ResolveDialog';
import { useTicketSession } from './TicketSessionProvider';

export function OutcomeBar({ ticket }: { ticket: Ticket }) {
  const { closeTicket, escalateTicket, workspaceViewByTicket } =
    useTicketSession();
  const workspaceView = workspaceViewByTicket[ticket.id] ?? null;

  return (
    <section
      aria-label="Ticket outcome"
      className="flex flex-col gap-3 rounded-md border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h2 className="text-sm font-bold text-text">Choose an outcome</h2>
        <p className="mt-1 text-xs text-text-muted">
          Resolve after verifying the result, or escalate when specialist review
          is needed.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <ResolveDialog
            documentationNote={ticket.notes.at(-1)?.body ?? ''}
            onConfirm={(options) => closeTicket(ticket.id, options)}
            status={ticket.status}
          />
          <span className="text-center text-[11px] text-text-muted">
            Eligibility reviewed before submission
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <EscalateDialog
            escalated={ticket.escalated}
            onConfirm={(details) => escalateTicket(ticket.id, details)}
            workspaceView={workspaceView}
          />
          <span className="text-center text-[11px] text-text-muted">
            {ticket.escalated ? 'Already recorded' : 'Available on every ticket'}
          </span>
        </div>
      </div>
    </section>
  );
}
