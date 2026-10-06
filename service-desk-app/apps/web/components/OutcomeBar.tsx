'use client';

import type { Ticket } from '@service-desk/shared';

import { EscalateDialog } from './EscalateDialog';
import { ResolveDialog } from './ResolveDialog';
import { useTicketSession } from './TicketSessionProvider';

export function OutcomeBar({ ticket }: { ticket: Ticket }) {
  const { closeTicket, escalateTicket, workspaceViewByTicket } =
    useTicketSession();
  const workspaceView = workspaceViewByTicket[ticket.id] ?? null;
  const workflowRecorded =
    workspaceView?.stages.every((stage) => stage.status === 'complete') ??
    false;

  return (
    <section
      aria-label="Ticket outcome"
      className="flex flex-col gap-3 rounded-md border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h2 className="text-sm font-bold text-text">Ticket outcome</h2>
        <p className="mt-1 text-xs text-text-muted">
          Verify the result and record your work before resolving. Escalate when
          specialist review is needed.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <ResolveDialog
            key={ticket.id}
            documentationNote={ticket.notes.at(-1)?.body ?? ''}
            onConfirm={(options) => closeTicket(ticket.id, options)}
            status={ticket.status}
            ticketId={ticket.id}
            workflowRecorded={workflowRecorded}
          />
          <span className="text-center text-[11px] text-text-muted">
            {workflowRecorded
              ? 'Review before final submission'
              : 'Review the remaining workflow before submitting'}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <EscalateDialog
            key={ticket.id}
            escalated={ticket.escalated}
            onConfirm={(details) => escalateTicket(ticket.id, details)}
            workspaceView={workspaceView}
          />
          <span className="text-center text-[11px] text-text-muted">
            {ticket.escalated
              ? 'Already recorded'
              : 'Available on every ticket'}
          </span>
        </div>
      </div>
    </section>
  );
}
