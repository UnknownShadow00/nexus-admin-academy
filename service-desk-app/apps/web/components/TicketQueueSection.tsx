import type { Ticket } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import type { Icon as TablerIcon } from '@tabler/icons-react';

import { TicketRow } from './TicketRow';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

interface TicketQueueSectionProps {
  icon: TablerIcon;
  label: string;
  meta: string;
  tickets: readonly Ticket[];
  assignmentByTicket: Readonly<Record<string, NexusAssignment>>;
}

export function TicketQueueSection({
  icon: Icon,
  label,
  meta,
  tickets,
  assignmentByTicket,
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
      <div className="hidden grid-cols-[8rem_minmax(0,1fr)_10rem_8rem_1.25rem] gap-3 border-y border-zinc-800 bg-zinc-950/50 px-4 py-2 text-[11px] font-extrabold uppercase tracking-wide text-zinc-600 sm:grid">
        <span>Priority</span>
        <span>Ticket</span>
        <span>Requester</span>
        <span>Status</span>
        <span />
      </div>
      <div className="divide-y divide-zinc-800">
        {tickets.map((ticket) => (
          <TicketRow
            assignment={assignmentByTicket[ticket.id]}
            key={ticket.id}
            ticket={ticket}
          />
        ))}
      </div>
    </Card>
  );
}
