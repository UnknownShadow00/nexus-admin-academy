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

const WORKFLOW_COPY: Readonly<
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
  experienceMode,
  stages,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  stages: readonly NexusWorkflowStage[];
}) {
  return (
    <section
      aria-labelledby="workflow-rail-title"
      className="sticky top-0 z-20 rounded-md border border-zinc-800 bg-zinc-950/95 px-3 py-3 shadow-lg backdrop-blur sm:px-4"
      data-group-2-slot="workflow-rail"
    >
      <h2 className="sr-only" id="workflow-rail-title">
        Ticket workflow
      </h2>
      <p className="sr-only">
        A checked circle means Completed, a dotted circle means Current step,
        and an empty circle means Not started.
      </p>
      <ol className="grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {stages.map((stage) => {
          const copy = WORKFLOW_COPY[stage.key];
          const help =
            stage.key === 'fix' && stage.mode === 'escalate'
              ? 'This ticket is likely not yours to fix directly — decide where it should go.'
              : copy.help;
          return (
            <li
              aria-current={stage.status === 'current' ? 'step' : undefined}
              className={`rounded-sm border p-2.5 ${
                stage.status === 'current'
                  ? 'border-sky-400/60 bg-sky-400/10 text-sky-100'
                  : stage.status === 'complete'
                    ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-100'
                    : 'border-zinc-800 bg-zinc-900 text-zinc-400'
              }`}
              key={stage.key}
            >
              <div className="flex items-center gap-2">
                <StageIcon status={stage.status} />
                <div>
                  <p className="text-sm font-bold">{copy.label}</p>
                  <p className="text-xs font-semibold">
                    {STATUS_COPY[stage.status]}
                  </p>
                </div>
              </div>
              {experienceMode !== 'assessment' ? (
                <p className="mt-2 text-xs leading-5 text-zinc-400">{help}</p>
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
