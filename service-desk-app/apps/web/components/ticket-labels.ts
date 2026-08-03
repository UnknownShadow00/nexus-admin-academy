import { TicketStatus } from '@service-desk/shared';

export const TICKET_STATUS_LABELS: Record<TicketStatus, string> = {
  [TicketStatus.Open]: 'Open',
  [TicketStatus.InProgress]: 'In Progress',
  [TicketStatus.Pending]: 'Pending',
  [TicketStatus.Resolved]: 'Resolved',
  [TicketStatus.Closed]: 'Closed',
};

export function formatActivityTimestamp(timestamp: string) {
  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(timestamp));
}
