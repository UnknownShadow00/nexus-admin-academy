'use client';

import type { Ticket } from '@service-desk/shared';
import { Badge, Card, PriorityBadge } from '@service-desk/ui';
import { IconArrowLeft, IconClockHour4 } from '@tabler/icons-react';
import Link from 'next/link';

import type { NexusAssignment } from '../lib/nexus-service-desk-client';
import { TicketStatusBadge } from './TicketStatusBadge';
import { useNexusReturnTarget } from './useNexusReturnTarget';

type ExperienceMode = NexusAssignment['experience_mode'];

const EXPERIENCE_MODE_LABELS: Record<ExperienceMode, string> = {
  assessment: 'Assessment',
  guided: 'Guided Practice',
  practice: 'Practice',
};

export function experienceModeLabel(mode: ExperienceMode): string {
  return EXPERIENCE_MODE_LABELS[mode];
}

export function attemptsRemaining(
  maximumAttempts: number | null,
  attemptNumber: number,
): number | null {
  return maximumAttempts === null ? null : maximumAttempts - attemptNumber + 1;
}

export function TicketContextBar({
  assignment,
  ticket,
}: {
  assignment?: NexusAssignment;
  ticket: Ticket;
}) {
  const returnTarget = useNexusReturnTarget();
  const remaining = assignment
    ? attemptsRemaining(
        assignment.maximum_attempts,
        assignment.most_recent_attempt?.attempt_number ?? 1,
      )
    : null;

  return (
    <Card>
      <div className="p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {returnTarget ? (
            <a
              className="sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm border border-sky-400/30 bg-sky-400/10 px-3 text-sm font-bold text-sky-200 hover:bg-sky-400/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              href={returnTarget.href}
            >
              <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
              {returnTarget.label}
            </a>
          ) : (
            <Link
              className="sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-semibold text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              href="/"
            >
              <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
              Back to queue
            </Link>
          )}
          {returnTarget ? (
            <Link
              className="sd-focus-ring inline-flex min-h-10 items-center rounded-sm px-2 text-sm font-semibold text-zinc-400 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              href="/"
            >
              Back to queue
            </Link>
          ) : null}
        </div>

        <div className="mt-4 flex min-w-0 flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold text-sky-400">
            {ticket.id}
          </span>
          <PriorityBadge pill priority={ticket.priority} />
          <TicketStatusBadge status={ticket.status} />
          {assignment ? (
            <Badge variant="sky">
              {experienceModeLabel(assignment.experience_mode)}
            </Badge>
          ) : null}
          {remaining !== null ? (
            <span className="ml-auto text-xs font-semibold text-zinc-400">
              Attempts remaining: {remaining}
            </span>
          ) : null}
        </div>
        <h1 className="mt-3 max-w-4xl font-display text-xl font-bold leading-snug text-zinc-100 sm:text-2xl">
          {ticket.title}
        </h1>
        <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400">
          <IconClockHour4 aria-hidden="true" className="h-4 w-4 text-sky-400" />
          <span>{ticket.sla.target}</span>
        </div>
        {assignment?.experience_mode === 'guided' ? (
          <p className="mt-3 max-w-3xl text-sm text-sky-200">
            Guided practice. This case may return later as an independent
            assessment.
          </p>
        ) : assignment?.experience_mode === 'practice' ? (
          <p className="mt-3 max-w-3xl text-sm text-zinc-400">
            Independent replay. Practice does not replace required assessment
            mastery or award XP.
          </p>
        ) : assignment?.guided_completed ? (
          <p className="mt-3 max-w-3xl text-sm text-sky-200">
            You practiced this case earlier. Complete it independently to
            demonstrate mastery.
          </p>
        ) : null}
      </div>
    </Card>
  );
}
