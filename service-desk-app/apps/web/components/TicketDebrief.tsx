'use client';

import type { Ticket } from '@service-desk/shared';
import { Button, Card, CardHeader } from '@service-desk/ui';
import {
  IconArrowLeft,
  IconCircleCheck,
  IconCircleDashed,
  IconCircleX,
  IconMinus,
  IconRefresh,
} from '@tabler/icons-react';
import Link from 'next/link';
import React, { useState } from 'react';

import type {
  NexusAssignment,
  NexusDebrief,
  NexusGrade,
} from '../lib/nexus-service-desk-client';
import { useNexusReturnTarget } from './useNexusReturnTarget';

export function learnerOutcomeCopy(grade: NexusGrade): string {
  if (grade.learner_outcome === 'awaiting_review')
    return 'Assessment result: AWAITING REVIEW — module credit pending.';
  if (!grade.passed)
    return 'Assessment result: NEEDS ANOTHER ATTEMPT — no module credit earned.';
  if (
    grade.learner_outcome === 'escalated_successfully' ||
    grade.debrief?.result.outcome === 'escalated'
  )
    return 'Assessment result: ESCALATED SUCCESSFULLY — module credit earned.';
  return 'Assessment result: PASS — module credit earned.';
}

const STATUS_ICON = {
  full: IconCircleCheck,
  partial: IconCircleDashed,
  missed: IconCircleX,
  not_applicable: IconMinus,
} as const;

const STATUS_LABEL = {
  full: 'Completed',
  partial: 'Partial',
  missed: 'Missed',
  not_applicable: 'Not applicable',
} as const;

/**
 * A failed attempt may be retried while the server still has an attempt left.
 * `attempts_remaining === null` means the assignment has no ceiling.
 */
export function canRetryAttempt(
  grade: NexusGrade,
  debrief: NexusDebrief | null | undefined,
): boolean {
  if (grade.passed) return false;
  const remaining = debrief?.result.attempts_remaining;
  if (remaining === undefined) return false;
  return remaining === null || remaining > 0;
}

export function TicketDebrief({
  assignment,
  grade,
  onRetry,
  ticket,
}: {
  assignment?: NexusAssignment;
  grade: NexusGrade;
  onRetry?: (ticketId: string) => Promise<boolean>;
  ticket: Ticket;
}) {
  const returnTarget = useNexusReturnTarget();
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState('');
  const debrief = grade.debrief;

  const showRetry = Boolean(onRetry) && canRetryAttempt(grade, debrief);
  // Server-sourced, never invented client-side: the label simply names the
  // attempt the server will create next.
  const nextAttemptNumber = assignment?.most_recent_attempt?.attempt_number;
  const retryLabel =
    typeof nextAttemptNumber === 'number'
      ? `Start attempt ${String(nextAttemptNumber + 1)}`
      : 'Try again';

  const BackLink = returnTarget ? 'a' : Link;
  const backLink = (
    <BackLink
      className={`sd-button ${
        showRetry ? 'sd-button--default' : 'sd-button--primary'
      } sd-focus-ring inline-flex min-h-10 items-center gap-2 px-4 py-2 font-bold`}
      href={returnTarget?.href ?? '/'}
    >
      <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
      {returnTarget ? returnTarget.label : 'Back to queue'}
    </BackLink>
  );

  const retryControls = showRetry ? (
    <>
      <Button
        disabled={retrying}
        onClick={() => {
          if (!onRetry) return;
          setRetryError('');
          setRetrying(true);
          void onRetry(ticket.id)
            .then((ok) => {
              if (!ok) {
                setRetryError(
                  'Nexus could not start another attempt for this ticket. Return to the queue and try again shortly.',
                );
              }
            })
            .catch(() => {
              setRetryError(
                'Nexus could not start another attempt for this ticket. Return to the queue and try again shortly.',
              );
            })
            .finally(() => setRetrying(false));
        }}
        variant="primary"
      >
        <IconRefresh aria-hidden="true" className="h-4 w-4" />
        {retrying ? 'Starting…' : retryLabel}
      </Button>
      {backLink}
    </>
  ) : (
    backLink
  );

  if (!debrief) {
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <Card>
          <div className="p-5">
            <h1 className="text-lg font-bold text-text">
              {learnerOutcomeCopy(grade)}
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              {grade.feedback_summary}
            </p>
            <p className="mt-2 text-sm text-text">
              Score: {grade.overall_score}
            </p>
          </div>
        </Card>
        <div className="flex flex-wrap gap-3">{retryControls}</div>
      </section>
    );
  }

  const { result } = debrief;
  const limited = debrief.coaching_tier === 'limited';

  return (
    <section
      aria-label="Ticket debrief"
      className="mx-auto max-w-3xl space-y-4"
    >
      <Card>
        <div className="p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">
            {ticket.id} · debrief
          </p>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1
              className={`text-2xl font-bold ${grade.passed ? 'text-success' : 'text-warning'}`}
            >
              {learnerOutcomeCopy(grade)}
            </h1>
            <span className="text-sm text-text">
              Process score {result.score}
            </span>
            {result.attempts_remaining !== null ? (
              <span className="text-sm text-text-muted">
                {result.attempts_remaining} attempt
                {result.attempts_remaining === 1 ? '' : 's'} remaining
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm text-text">{grade.feedback_summary}</p>
        </div>
      </Card>

      {debrief.categories.length > 0 ? (
        <Card>
          <CardHeader
            meta={limited ? 'Where to focus' : 'What counted'}
            title="Process"
          />
          <ul className="divide-y divide-border">
            {debrief.categories.map((category) => {
              const Icon = STATUS_ICON[category.status];
              return (
                <li className="flex gap-3 p-4" key={category.key}>
                  <Icon
                    aria-hidden="true"
                    className={`mt-0.5 h-5 w-5 shrink-0 ${
                      category.status === 'full'
                        ? 'text-success'
                        : category.status === 'missed'
                          ? 'text-warning'
                          : 'text-text-muted'
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-sm font-bold text-text">
                        {category.label}
                      </span>
                      <span className="text-xs text-text-muted">
                        {STATUS_LABEL[category.status]}
                        {category.status === 'not_applicable'
                          ? ''
                          : ` · ${category.points}/${category.max}`}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-text-muted">
                      {category.explanation}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}

      <Card>
        <CardHeader meta="Your words" title="Your documentation" />
        <div className="p-4">
          <p className="whitespace-pre-wrap rounded-sm border border-border bg-surface p-3 text-sm text-text">
            {debrief.student_note || 'No closure note was recorded.'}
          </p>
          <ul className="mt-3 flex flex-wrap gap-3 text-xs text-text-muted">
            {(
              [
                ['cause', 'States the cause'],
                ['action', 'States the action taken'],
                ['verification', 'States how it was verified'],
              ] as const
            ).map(([key, label]) => (
              <li className="flex items-center gap-1" key={key}>
                {debrief.note_dimensions[key] ? (
                  <IconCircleCheck
                    aria-hidden="true"
                    className="h-4 w-4 text-success"
                  />
                ) : (
                  <IconCircleDashed
                    aria-hidden="true"
                    className="h-4 w-4 text-text-muted"
                  />
                )}
                {label}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-text-muted">
            These notes-quality hints are advisory and do not change your score.
          </p>
        </div>
      </Card>

      {limited ? (
        <Card>
          <CardHeader
            meta="Coaching"
            title="Work it out on your next attempt"
          />
          <p className="p-4 text-sm text-text-muted">
            You still have a graded attempt left, so the worked solution stays
            hidden. Use the areas above to decide what evidence to gather, what
            action the ticket really needs, and what to document. The full
            walkthrough is released once you pass or use your last attempt.
          </p>
        </Card>
      ) : null}

      {debrief.stronger_path.length ? (
        <Card>
          <CardHeader
            meta="For next time"
            title="A stronger troubleshooting path"
          />
          <ol className="list-decimal space-y-1 p-4 pl-8 text-sm text-text">
            {debrief.stronger_path.map((step, index) => (
              <li key={`${String(index)}-${step}`}>{step}</li>
            ))}
          </ol>
        </Card>
      ) : null}

      {debrief.escalation_feedback ? (
        <Card>
          <CardHeader
            meta="Judgement"
            title="Would escalation have been right?"
          />
          <div className="p-4 text-sm text-text">
            <p className="font-bold text-text">
              {debrief.escalation_feedback.appropriate ? 'Yes' : 'No'}
            </p>
            <p className="mt-1 text-text-muted">
              {debrief.escalation_feedback.text}
            </p>
          </div>
        </Card>
      ) : null}

      {retryError ? (
        <p
          className="rounded-sm border border-warning/40 bg-warning/10 p-3 text-sm font-semibold text-text"
          role="alert"
        >
          {retryError}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">{retryControls}</div>
    </section>
  );
}
