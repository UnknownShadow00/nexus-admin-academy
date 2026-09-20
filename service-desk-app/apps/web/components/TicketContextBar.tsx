'use client';

import type { Ticket } from '@service-desk/shared';
import { PriorityBadge } from '@service-desk/ui';
import { IconArrowLeft } from '@tabler/icons-react';
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
  completed = false,
}: {
  assignment?: NexusAssignment;
  ticket: Ticket;
  completed?: boolean;
}) {
  const returnTarget = useNexusReturnTarget();
  const remaining = assignment
    ? attemptsRemaining(
        assignment.maximum_attempts,
        assignment.most_recent_attempt?.attempt_number ?? 1,
      )
    : null;

  return (
    <header className="min-w-0 border-b border-border pb-4">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          {returnTarget ? (
            <a
              className="sd-focus-ring inline-flex min-h-11 items-center gap-2 rounded-sm text-sm font-semibold text-text-muted hover:text-text"
              href={returnTarget.href}
            >
              <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
              {returnTarget.label}
            </a>
          ) : (
            <Link
              className="sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-semibold text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              href="/"
            >
              <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
              Back to queue
            </Link>
          )}
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold text-text-muted">
            {ticket.id}
          </span>
          <PriorityBadge pill priority={ticket.priority} />
          <TicketStatusBadge status={ticket.status} />
          {assignment ? (
            <span className="text-xs text-text-muted">
              {experienceModeLabel(assignment.experience_mode)}
            </span>
          ) : null}
          {!completed && remaining !== null ? (
            <span className="ml-auto text-xs font-semibold text-text-muted">
              Attempts remaining: {remaining}
            </span>
          ) : null}
        </div>
        <h1 className="mt-2 max-w-4xl break-words font-display text-lg font-bold leading-snug text-text sm:text-xl">
          {ticket.title}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-muted">
          <span>{ticket.requester.name}</span>
          <span className="font-mono">{ticket.device.assetTag}</span>
        </div>
        {assignment?.experience_mode === 'guided' ? (
          <p className="mt-2 hidden max-w-3xl text-xs text-text-muted sm:block">
            Guided practice. This case may return later as an independent
            assessment.
          </p>
        ) : assignment?.experience_mode === 'practice' ? (
          <p className="mt-2 max-w-3xl text-xs text-text-muted">
            Independent replay. Practice does not replace required assessment
            mastery or award XP.
          </p>
        ) : assignment?.guided_completed ? (
          <p className="mt-2 max-w-3xl text-xs text-text-muted">
            You practiced this case earlier. Complete it independently to
            demonstrate mastery.
          </p>
        ) : null}
      </div>
    </header>
  );
}
