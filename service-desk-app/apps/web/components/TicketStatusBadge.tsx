import { TicketStatus } from '@service-desk/shared';
import { Badge } from '@service-desk/ui';

import { TICKET_STATUS_LABELS } from './ticket-labels';

const STATUS_VARIANTS: Record<
  TicketStatus,
  'amber' | 'default' | 'sky' | 'success'
> = {
  [TicketStatus.Open]: 'default',
  [TicketStatus.InProgress]: 'sky',
  [TicketStatus.Pending]: 'amber',
  [TicketStatus.Resolved]: 'success',
  [TicketStatus.Closed]: 'default',
};

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  return (
    <Badge variant={STATUS_VARIANTS[status]}>
      {TICKET_STATUS_LABELS[status]}
    </Badge>
  );
}
