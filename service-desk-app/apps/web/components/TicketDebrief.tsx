'use client';

import type { Ticket } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import {
  IconArrowLeft,
  IconCircleCheck,
  IconCircleDashed,
  IconCircleX,
  IconMinus,
} from '@tabler/icons-react';
import Link from 'next/link';

import type { NexusDebrief, NexusGrade } from '../lib/nexus-service-desk-client';
import { useNexusReturnTarget } from './useNexusReturnTarget';

const OUTCOME_COPY: Record<
  NexusDebrief['result']['outcome'],
  { title: string; tone: string }
> = {
  resolved: { title: 'Resolved', tone: 'text-success' },
  escalated: { title: 'Escalated', tone: 'text-accent' },
  needs_another_try: { title: 'Needs another try', tone: 'text-warning' },
};

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

export function TicketDebrief({
  grade,
  ticket,
}: {
  grade: NexusGrade;
  ticket: Ticket;
}) {
  const returnTarget = useNexusReturnTarget();
  const debrief = grade.debrief;

  if (!debrief) {
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <Card>
          <div className="p-5">
            <h1 className="text-lg font-bold text-text">
              {ticket.id} · {grade.passed ? 'Passed' : 'Not passed'}
            </h1>
            <p className="mt-1 text-sm text-text-muted">{grade.feedback_summary}</p>
            <p className="mt-2 text-sm text-text">
              Score: {grade.overall_score}
            </p>
          </div>
        </Card>
      </section>
    );
  }

  const { result } = debrief;
  const outcome = OUTCOME_COPY[result.outcome];

  return (
    <section aria-label="Ticket debrief" className="mx-auto max-w-3xl space-y-4">
      <Card>
        <div className="p-5">
          <p className="text-xs font-bold uppercase tracking-wide text-text-muted">
            {ticket.id} · debrief
          </p>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 className={`text-2xl font-bold ${outcome.tone}`}>
              {outcome.title}
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

      <Card>
        <CardHeader meta="What counted" title="Process" />
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

      {debrief.stronger_path.length ? (
        <Card>
          <CardHeader meta="For next time" title="A stronger troubleshooting path" />
          <ol className="list-decimal space-y-1 p-4 pl-8 text-sm text-text">
            {debrief.stronger_path.map((step, index) => (
              <li key={`${index}-${step}`}>{step}</li>
            ))}
          </ol>
        </Card>
      ) : null}

      <Card>
        <CardHeader meta="Judgement" title="Would escalation have been right?" />
        <div className="p-4 text-sm text-text">
          <p className="font-bold text-text">
            {debrief.escalation_feedback.appropriate ? 'Yes' : 'No'}
          </p>
          <p className="mt-1 text-text-muted">{debrief.escalation_feedback.text}</p>
        </div>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Link
          className="sd-button sd-button--primary sd-focus-ring inline-flex min-h-10 items-center gap-2 px-4 py-2 font-bold"
          href={returnTarget?.href ?? '/'}
        >
          <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
          {returnTarget ? returnTarget.label : 'Back to queue'}
        </Link>
      </div>
    </section>
  );
}
