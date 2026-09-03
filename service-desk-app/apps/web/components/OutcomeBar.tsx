'use client';

import type { Ticket } from '@service-desk/shared';

import { EscalateDialog } from './EscalateDialog';
import { ResolveDialog } from './ResolveDialog';
import { useAttemptScore, useTicketSession } from './TicketSessionProvider';

export function OutcomeBar({ ticket }: { ticket: Ticket }) {
  const { previewCloseGrade } = useAttemptScore();
  const { closeTicket, escalateTicket, workspaceViewByTicket } =
    useTicketSession();
  const workspaceView = workspaceViewByTicket[ticket.id] ?? null;

  return (
    <section
      aria-label="Ticket outcome"
      className="flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h2 className="text-sm font-bold text-zinc-100">Choose an outcome</h2>
        <p className="mt-1 text-xs text-zinc-400">
          Resolve after verifying the result, or escalate when specialist review
          is needed.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <ResolveDialog
            initialResolutionNote={ticket.notes.at(-1)?.body ?? ''}
            onConfirm={(options) => closeTicket(ticket.id, options)}
            readyGrade={previewCloseGrade(ticket.id, true)}
            status={ticket.status}
            unresolvedGrade={previewCloseGrade(ticket.id, false)}
          />
          <span className="text-center text-[11px] text-zinc-500">
            Eligibility reviewed before submission
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <EscalateDialog
            escalated={ticket.escalated}
            onConfirm={(details) => escalateTicket(ticket.id, details)}
            workspaceView={workspaceView}
          />
          <span className="text-center text-[11px] text-zinc-500">
            {ticket.escalated
              ? 'Already recorded'
              : workspaceView?.escalation
                ? `Routes to ${workspaceView.escalation.route}`
                : 'Available'}
          </span>
        </div>
      </div>
    </section>
  );
}
