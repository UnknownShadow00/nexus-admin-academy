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
  resolved: { title: 'Resolved', tone: 'text-emerald-300' },
  escalated: { title: 'Escalated', tone: 'text-sky-300' },
  needs_another_try: { title: 'Needs another try', tone: 'text-amber-300' },
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
            <h1 className="text-lg font-bold text-zinc-100">
              {ticket.id} · {grade.passed ? 'Passed' : 'Not passed'}
            </h1>
            <p className="mt-1 text-sm text-zinc-400">{grade.feedback_summary}</p>
            <p className="mt-2 text-sm text-zinc-300">
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
          <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
            {ticket.id} · debrief
          </p>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h1 className={`text-2xl font-bold ${outcome.tone}`}>
              {outcome.title}
            </h1>
            <span className="text-sm text-zinc-300">
              Process score {result.score}
            </span>
            {result.attempts_remaining !== null ? (
              <span className="text-sm text-zinc-400">
                {result.attempts_remaining} attempt
                {result.attempts_remaining === 1 ? '' : 's'} remaining
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm text-zinc-300">{grade.feedback_summary}</p>
        </div>
      </Card>

      <Card>
        <CardHeader meta="What counted" title="Process" />
        <ul className="divide-y divide-zinc-800">
          {debrief.categories.map((category) => {
            const Icon = STATUS_ICON[category.status];
            return (
              <li className="flex gap-3 p-4" key={category.key}>
                <Icon
                  aria-hidden="true"
                  className={`mt-0.5 h-5 w-5 shrink-0 ${
                    category.status === 'full'
                      ? 'text-emerald-400'
                      : category.status === 'missed'
                        ? 'text-amber-400'
                        : 'text-zinc-500'
                  }`}
                />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-sm font-bold text-zinc-100">
                      {category.label}
                    </span>
                    <span className="text-xs text-zinc-400">
                      {STATUS_LABEL[category.status]}
                      {category.status === 'not_applicable'
                        ? ''
                        : ` · ${category.points}/${category.max}`}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-400">
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
          <p className="whitespace-pre-wrap rounded-sm border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-200">
            {debrief.student_note || 'No closure note was recorded.'}
          </p>
          <ul className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-400">
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
                    className="h-4 w-4 text-emerald-400"
                  />
                ) : (
                  <IconCircleDashed
                    aria-hidden="true"
                    className="h-4 w-4 text-zinc-600"
                  />
                )}
                {label}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-zinc-500">
            These notes-quality hints are advisory and do not change your score.
          </p>
        </div>
      </Card>

      {debrief.stronger_path.length ? (
        <Card>
          <CardHeader meta="For next time" title="A stronger troubleshooting path" />
          <ol className="list-decimal space-y-1 p-4 pl-8 text-sm text-zinc-300">
            {debrief.stronger_path.map((step, index) => (
              <li key={`${index}-${step}`}>{step}</li>
            ))}
          </ol>
        </Card>
      ) : null}

      <Card>
        <CardHeader meta="Judgement" title="Would escalation have been right?" />
        <div className="p-4 text-sm text-zinc-300">
          <p className="font-bold text-zinc-100">
            {debrief.escalation_feedback.appropriate ? 'Yes' : 'No'}
          </p>
          <p className="mt-1 text-zinc-400">{debrief.escalation_feedback.text}</p>
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
