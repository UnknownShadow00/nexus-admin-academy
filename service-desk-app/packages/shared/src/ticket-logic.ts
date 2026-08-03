import { Priority } from './enums';
import { TicketStatus, type Ticket } from './ticket-types';

export const CLOSED_TICKET_STATUSES = [
  TicketStatus.Resolved,
  TicketStatus.Closed,
] as const;

export interface TicketFilters {
  priority: Priority | 'all';
  query: string;
  status: TicketStatus | 'all';
}

const STATUS_TRANSITIONS: Record<TicketStatus, readonly TicketStatus[]> = {
  [TicketStatus.Open]: [
    TicketStatus.InProgress,
    TicketStatus.Pending,
    TicketStatus.Resolved,
    TicketStatus.Closed,
  ],
  [TicketStatus.InProgress]: [
    TicketStatus.Open,
    TicketStatus.Pending,
    TicketStatus.Resolved,
    TicketStatus.Closed,
  ],
  [TicketStatus.Pending]: [
    TicketStatus.Open,
    TicketStatus.InProgress,
    TicketStatus.Resolved,
    TicketStatus.Closed,
  ],
  [TicketStatus.Resolved]: [TicketStatus.InProgress, TicketStatus.Closed],
  [TicketStatus.Closed]: [TicketStatus.Open],
};

export function getStatusTransitions(status: TicketStatus) {
  return STATUS_TRANSITIONS[status];
}

export function isOpenTicket(ticket: Pick<Ticket, 'status'>) {
  return !CLOSED_TICKET_STATUSES.includes(
    ticket.status as (typeof CLOSED_TICKET_STATUSES)[number],
  );
}

export function filterTickets(
  tickets: readonly Ticket[],
  filters: TicketFilters,
) {
  const query = filters.query.trim().toLocaleLowerCase();

  return tickets.filter((ticket) => {
    const matchesQuery =
      query.length === 0 ||
      [ticket.id, ticket.title, ticket.requester.name].some((value) =>
        value.toLocaleLowerCase().includes(query),
      );
    const matchesPriority =
      filters.priority === 'all' || ticket.priority === filters.priority;
    const matchesStatus =
      filters.status === 'all' || ticket.status === filters.status;

    return matchesQuery && matchesPriority && matchesStatus;
  });
}

export function initialHintRevealCount(totalSteps: number) {
  return totalSteps > 0 ? 1 : 0;
}

export function nextHintRevealCount(current: number, totalSteps: number) {
  return Math.min(Math.max(current, 0) + 1, Math.max(totalSteps, 0));
}

export interface CloseReview {
  kind: 'ready' | 'unresolved-warning';
  message: string;
}

export function getCloseReview(
  status: TicketStatus,
  confirmedResolved: boolean,
): CloseReview {
  if (
    confirmedResolved ||
    status === TicketStatus.Resolved ||
    status === TicketStatus.Closed
  ) {
    return {
      kind: 'ready',
      message: 'The ticket is ready for a final resolution note.',
    };
  }

  return {
    kind: 'unresolved-warning',
    message:
      'This ticket is not marked resolved. Closing it now may leave the requester without a verified outcome.',
  };
}

export function formatRelativeTime(isoTimestamp: string, nowIso: string) {
  const elapsedMinutes = Math.max(
    0,
    Math.round(
      (new Date(nowIso).getTime() - new Date(isoTimestamp).getTime()) / 60_000,
    ),
  );

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) {
    return `${elapsedHours}h ago`;
  }

  return `${Math.floor(elapsedHours / 24)}d ago`;
}

export function formatDueIndicator(dueAt: string, nowIso: string) {
  const remainingMinutes = Math.round(
    (new Date(dueAt).getTime() - new Date(nowIso).getTime()) / 60_000,
  );

  if (remainingMinutes <= 0) {
    return 'SLA overdue';
  }

  if (remainingMinutes < 60) {
    return `Due in ${remainingMinutes}m`;
  }

  const hours = Math.floor(remainingMinutes / 60);
  const minutes = remainingMinutes % 60;
  return minutes > 0 ? `Due in ${hours}h ${minutes}m` : `Due in ${hours}h`;
}
