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

function StageItem({
  stage,
  index,
}: {
  stage: NexusWorkflowStage;
  index: number;
}) {
  const current = stage.status === 'current';
  return (
    <li
      aria-current={current ? 'step' : undefined}
      className={`min-w-0 border-l-[3px] px-3 py-2 ${
        current
          ? 'border-accent bg-accent/10 text-text'
          : 'border-border bg-surface-raised/50 text-text-muted'
      }`}
    >
      <div className="flex items-start gap-2">
        <StageIcon status={stage.status} />
        <div className="min-w-0">
          <p className="text-xs font-bold leading-snug text-text">
            {index + 1}. {WORKFLOW_COPY[stage.key].label}
          </p>
          <p className="mt-0.5 text-[11px] leading-snug">
            {STATUS_COPY[stage.status]}
          </p>
        </div>
      </div>
    </li>
  );
}

export function WorkflowRail({
  stages,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  stages: readonly NexusWorkflowStage[];
}) {
  const currentIndex = stages.findIndex((stage) => stage.status === 'current');
  const currentStage = currentIndex >= 0 ? stages[currentIndex] : undefined;
  return (
    <section
      aria-labelledby="workflow-rail-title"
      className="sd-workflow min-w-0 border-b border-border pb-4"
      data-group-2-slot="workflow-rail"
    >
      <h2 className="sr-only" id="workflow-rail-title">
        Ticket workflow
      </h2>
      <p className="sr-only">
        A checked circle means Completed, a dotted circle means Current step,
        and an empty circle means Not started.
      </p>
      <ol className="hidden gap-1 sm:grid sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        {stages.map((stage, index) => (
          <StageItem index={index} key={stage.key} stage={stage} />
        ))}
      </ol>
      <details className="rounded-md border border-border bg-surface-raised sm:hidden">
        <summary className="sd-focus-ring min-h-12 cursor-pointer px-3 py-3 text-sm font-semibold text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus">
          {currentStage
            ? `Step ${currentIndex + 1} of ${stages.length}: ${WORKFLOW_COPY[currentStage.key].label}`
            : 'Ticket workflow'}
          <span className="ml-2 text-xs font-normal text-text-muted">
            View all stages
          </span>
        </summary>
        <ol className="grid gap-1 border-t border-border p-2">
          {stages.map((stage, index) => (
            <StageItem index={index} key={stage.key} stage={stage} />
          ))}
        </ol>
      </details>
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
