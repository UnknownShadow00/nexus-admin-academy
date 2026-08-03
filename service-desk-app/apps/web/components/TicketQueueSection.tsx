import type { Ticket } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import type { Icon as TablerIcon } from '@tabler/icons-react';

import { TicketRow } from './TicketRow';

interface TicketQueueSectionProps {
  icon: TablerIcon;
  label: string;
  meta: string;
  tickets: readonly Ticket[];
}

export function TicketQueueSection({
  icon: Icon,
  label,
  meta,
  tickets,
}: TicketQueueSectionProps) {
  return (
    <Card aria-label={label}>
      <CardHeader
        meta={meta}
        title={
          <span className="flex items-center gap-2">
            <Icon aria-hidden="true" className="h-5 w-5 text-sky-400" />
            {label}
          </span>
        }
      />
      <div className="divide-y divide-zinc-800">
        {tickets.map((ticket) => (
          <TicketRow key={ticket.id} ticket={ticket} />
        ))}
      </div>
    </Card>
  );
}
