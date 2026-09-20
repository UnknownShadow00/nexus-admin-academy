import {
  IconCircle,
  IconCircleCheck,
  IconCircleDot,
} from '@tabler/icons-react';
import React from 'react';

import type {
  NexusWorkflowStage,
  NexusWorkflowStageKey,
} from '../lib/nexus-service-desk-client';

export const WORKFLOW_COPY: Readonly<
  Record<NexusWorkflowStageKey, { label: string; help: string }>
> = {
  understand: {
    label: 'Understand',
    help: 'Read what the user reports and what work is affected.',
  },
  investigate: {
    label: 'Investigate',
    help: 'Find out what is actually happening before you change anything.',
  },
  diagnose: {
    label: 'Diagnose',
    help: 'Decide what is causing the problem based on your evidence.',
  },
  fix: {
    label: 'Fix / Escalate',
    help: 'Make a safe change, or send the ticket to the right team.',
  },
  verify: {
    label: 'Verify',
    help: 'Prove the original problem is gone.',
  },
  document: {
    label: 'Document',
    help: 'Write down what you found, changed, and verified.',
  },
};

const STATUS_COPY = {
  complete: 'Completed',
  current: 'Current step',
  not_started: 'Not started',
} as const;

function StageIcon({ status }: Pick<NexusWorkflowStage, 'status'>) {
  const Icon =
    status === 'complete'
      ? IconCircleCheck
      : status === 'current'
        ? IconCircleDot
        : IconCircle;
  return <Icon aria-hidden="true" className="h-5 w-5 shrink-0" />;
}

export function WorkflowRail({
  stages,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  stages: readonly NexusWorkflowStage[];
}) {
  return (
    <section
      aria-labelledby="workflow-rail-title"
      className="min-w-0 border-b border-border pb-3"
      data-group-2-slot="workflow-rail"
    >
      <h2 className="sr-only" id="workflow-rail-title">
        Ticket workflow
      </h2>
      <p className="sr-only">
        A checked circle means Completed, a dotted circle means Current step,
        and an empty circle means Not started.
      </p>
      <ol className="hidden flex-wrap gap-x-5 gap-y-2 sm:flex">
        {stages.map((stage) => {
          const copy = WORKFLOW_COPY[stage.key];
          // No per-stage escalation hint: the workspace must never signal that
          // escalation is the expected outcome before the student decides.
          return (
            <li
              aria-current={stage.status === 'current' ? 'step' : undefined}
              className={`py-1 ${
                stage.status === 'current'
                  ? 'font-semibold text-text'
                  : stage.status === 'complete'
                    ? 'text-text'
                    : 'text-text-muted'
              }`}
              key={stage.key}
            >
              <div className="flex items-center gap-2">
                <StageIcon status={stage.status} />
                <div>
                  <p className="text-sm font-bold">{copy.label}</p>
                  <p className="sr-only">{STATUS_COPY[stage.status]}</p>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="text-sm text-text sm:hidden">
        Current stage:{' '}
        {
          WORKFLOW_COPY[
            stages.find((stage) => stage.status === 'current')?.key ??
              'document'
          ].label
        }
      </p>
    </section>
  );
}

export function CurrentStage({
  stages,
  experienceMode,
}: {
  stages: readonly NexusWorkflowStage[];
  experienceMode: 'guided' | 'practice' | 'assessment';
}) {
  const current = stages.find((stage) => stage.status === 'current');
  if (!current) return null;
  return (
    <section aria-label="Current stage" className="border-b border-border pb-3">
      <h2 className="text-sm font-semibold text-text">
        Current stage: {WORKFLOW_COPY[current.key].label}
      </h2>
      {experienceMode !== 'assessment' ? (
        <p className="mt-1 text-sm text-text-muted">
          {WORKFLOW_COPY[current.key].help}
        </p>
      ) : null}
    </section>
  );
}
