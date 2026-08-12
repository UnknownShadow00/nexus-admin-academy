import type { Ticket } from '@service-desk/shared';
import { Badge, Card, PriorityBadge } from '@service-desk/ui';
import { IconAlertTriangle, IconClockHour4 } from '@tabler/icons-react';

import { TicketStatusBadge } from './TicketStatusBadge';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

export function TicketDetailHeader({
  assignment,
  ticket,
}: {
  assignment?: NexusAssignment;
  ticket: Ticket;
}) {
  return (
    <Card>
      <div className="border-b border-zinc-800 bg-zinc-800/40 px-4 py-4 sm:px-6 sm:py-5">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold text-sky-400">
            {ticket.id}
          </span>
          <PriorityBadge pill priority={ticket.priority} />
          <TicketStatusBadge status={ticket.status} />
          {assignment?.difficulty_label ? (
            <Badge>
              <span aria-hidden="true" className="text-amber-400">
                {assignment.difficulty_stars}
              </span>{' '}
              {assignment.difficulty_label}
            </Badge>
          ) : null}
          {assignment?.experience_mode ? (
            <Badge variant="sky">
              {assignment.experience_mode[0]?.toUpperCase()}
              {assignment.experience_mode.slice(1)}
            </Badge>
          ) : null}
          {ticket.escalated ? (
            <Badge className="gap-1" variant="amber">
              <IconAlertTriangle aria-hidden="true" className="h-3.5 w-3.5" />
              Escalated
            </Badge>
          ) : null}
        </div>
        <h1 className="mt-3 max-w-4xl font-display text-xl font-bold leading-snug text-zinc-100 sm:text-2xl">
          {ticket.title}
        </h1>
        <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400">
          <IconClockHour4 aria-hidden="true" className="h-4 w-4 text-sky-400" />
          <span>{ticket.sla.target}</span>
        </div>
      </div>
    </Card>
  );
}
