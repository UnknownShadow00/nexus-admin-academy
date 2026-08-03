'use client';

import type { Ticket } from '@service-desk/shared';

import { AssignmentControls } from './AssignmentControls';
import { EscalateDialog } from './EscalateDialog';
import { HintDialog } from './HintDialog';
import { ResolveDialog } from './ResolveDialog';
import { StatusMenu } from './StatusMenu';
import { useAttemptScore, useTicketSession } from './TicketSessionProvider';

export function TicketActionBar({ ticket }: { ticket: Ticket }) {
  const { previewCloseGrade } = useAttemptScore();
  const {
    assignTicket,
    changeStatus,
    closeTicket,
    escalateTicket,
    recordHintReveal,
    unassignTicket,
  } = useTicketSession();

  return (
    <section
      aria-label="Ticket actions"
      className="flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-3 sm:flex-row sm:flex-wrap sm:items-center sm:p-4"
    >
      <AssignmentControls
        assigned={ticket.assignedTo === 'you'}
        onAssign={() => assignTicket(ticket.id)}
        onUnassign={() => unassignTicket(ticket.id)}
      />
      <StatusMenu
        onChange={(status) => changeStatus(ticket.id, status)}
        status={ticket.status}
      />
      <div className="hidden h-6 w-px bg-zinc-700/50 sm:block" />
      <EscalateDialog
        escalated={ticket.escalated}
        onConfirm={() => escalateTicket(ticket.id)}
      />
      <ResolveDialog
        readyGrade={previewCloseGrade(ticket.id, true)}
        onConfirm={(options) => closeTicket(ticket.id, options)}
        status={ticket.status}
        unresolvedGrade={previewCloseGrade(ticket.id, false)}
      />
      <div className="sm:ml-auto">
        <HintDialog
          hints={ticket.hints}
          onReveal={(step) => recordHintReveal(ticket.id, step)}
          revealedCount={ticket.hintsRevealedCount}
        />
      </div>
    </section>
  );
}
