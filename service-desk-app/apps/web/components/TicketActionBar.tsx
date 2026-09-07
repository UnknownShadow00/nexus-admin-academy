'use client';

import type { Ticket } from '@service-desk/shared';
import React from 'react';

import { AssignmentControls } from './AssignmentControls';
import { StatusMenu } from './StatusMenu';
import { useSessionIdentity, useTicketSession } from './TicketSessionProvider';

export function TicketActionBar({ ticket }: { ticket: Ticket }) {
  const identity = useSessionIdentity();
  const { assignTicket, changeStatus, unassignTicket } = useTicketSession();

  return (
    <section
      aria-label="Ticket actions"
      className="flex flex-col gap-3 rounded-md border border-border bg-surface-raised p-3 sm:flex-row sm:flex-wrap sm:items-center sm:p-4"
    >
      <AssignmentControls
        assigned={ticket.assignedTo === 'you'}
        onAssign={() => assignTicket(ticket.id)}
        onUnassign={() => unassignTicket(ticket.id)}
      />
      {identity.isAdmin || identity.isMentor ? (
        <StatusMenu
          onChange={(status) => changeStatus(ticket.id, status)}
          status={ticket.status}
        />
      ) : (
        <span className="text-sm text-text-muted">
          Operational status: {ticket.status}
        </span>
      )}
    </section>
  );
}
