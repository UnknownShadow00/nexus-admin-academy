'use client';

import {
  ESCALATION_REASONS,
  ESCALATION_REASON_DESCRIPTIONS,
  ESCALATION_REASON_LABELS,
  ESCALATION_ROUTES,
  type EscalationReason,
  type EscalationRoute,
} from '@service-desk/shared';
import { Button, Modal } from '@service-desk/ui';
import { IconArrowUpRight, IconInfoCircle } from '@tabler/icons-react';
import React, { useState } from 'react';

import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

interface EscalateDialogProps {
  escalated: boolean;
  /** Server-authoritative workspace state for this ticket, if loaded. */
  workspaceView?: NexusWorkspaceView | null;
  onConfirm: (details: {
    reason: string;
    routeTeam: string;
    context?: string;
  }) => void;
}

export function investigationReady(
  workspaceView: NexusWorkspaceView | null | undefined,
): boolean {
  if (!workspaceView) return true;
  const done = new Set(
    workspaceView.stages
      .filter((stage) => stage.status === 'complete')
      .map((stage) => stage.key),
  );
  return done.has('investigate') && done.has('diagnose');
}

/**
 * The escalation form body.
 *
 * The student picks BOTH the reason and the destination team. Nothing here
 * says whether escalation is the right call for this ticket or which team is
 * correct - the server grades that after submission
 * (`service_desk_grading.compute_grade`). Rendered separately from the modal
 * shell so it can be asserted without a DOM.
 */
export function EscalationForm({
  context,
  onContextChange,
  onReasonChange,
  onRouteTeamChange,
  reason,
  ready,
  routeTeam,
}: {
  context: string;
  onContextChange: (value: string) => void;
  onReasonChange: (value: EscalationReason | '') => void;
  onRouteTeamChange: (value: EscalationRoute | '') => void;
  reason: EscalationReason | '';
  ready: boolean;
  routeTeam: EscalationRoute | '';
}) {
  return (
    <>
      {!ready ? (
        <div className="mt-1 flex gap-2 rounded-sm border border-warning/40 bg-warning/10 p-3 text-sm text-text">
          <IconInfoCircle
            aria-hidden="true"
            className="h-5 w-5 shrink-0 text-warning"
          />
          <p>
            Finish investigating and diagnosing the problem before you escalate,
            so the receiving team has your findings.
          </p>
        </div>
      ) : null}

      <label
        className="mt-4 block text-sm font-bold text-text"
        htmlFor="escalate-reason"
      >
        Reason for escalation
      </label>
      <select
        aria-describedby={reason ? 'escalate-reason-help' : undefined}
        className="sd-focus-ring mt-2 w-full rounded-sm border border-border bg-surface p-2 text-sm text-text"
        id="escalate-reason"
        onChange={(event) =>
          onReasonChange(event.target.value as EscalationReason | '')
        }
        value={reason}
      >
        <option value="">Choose a reason…</option>
        {ESCALATION_REASONS.map((value) => (
          <option key={value} value={value}>
            {ESCALATION_REASON_LABELS[value]}
          </option>
        ))}
      </select>
      {reason ? (
        <p className="mt-1 text-xs text-text-muted" id="escalate-reason-help">
          {ESCALATION_REASON_DESCRIPTIONS[reason]}
        </p>
      ) : null}

      <label
        className="mt-4 block text-sm font-bold text-text"
        htmlFor="escalate-destination"
      >
        Destination team
      </label>
      <select
        aria-describedby="escalate-destination-help"
        className="sd-focus-ring mt-2 w-full rounded-sm border border-border bg-surface p-2 text-sm text-text"
        id="escalate-destination"
        onChange={(event) =>
          onRouteTeamChange(event.target.value as EscalationRoute | '')
        }
        value={routeTeam}
      >
        <option value="">Choose a team…</option>
        {ESCALATION_ROUTES.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-text-muted" id="escalate-destination-help">
        Pick the team that owns the fix. Nexus checks your choice after you
        submit.
      </p>

      <label
        className="mt-4 block text-sm font-bold text-text"
        htmlFor="escalate-context"
      >
        Context for the receiving team{' '}
        <span className="font-normal text-text-muted">(optional)</span>
      </label>
      <textarea
        className="sd-focus-ring mt-2 min-h-20 w-full rounded-sm border border-border bg-surface p-2 text-sm font-normal text-text"
        id="escalate-context"
        maxLength={1000}
        onChange={(event) => onContextChange(event.target.value)}
        placeholder="What you found and why this needs another team."
        value={context}
      />
    </>
  );
}

export function EscalateDialog({
  escalated,
  workspaceView,
  onConfirm,
}: EscalateDialogProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<EscalationReason | ''>('');
  const [routeTeam, setRouteTeam] = useState<EscalationRoute | ''>('');
  const [context, setContext] = useState('');

  const ready = investigationReady(workspaceView);
  const canConfirm =
    Boolean(reason) && Boolean(routeTeam) && ready && !escalated;

  return (
    <Modal
      description="Route this incident to the team that owns it. You decide whether escalation is the right call."
      onOpenChange={setOpen}
      open={open}
      title="Escalate ticket"
      trigger={
        <Button disabled={escalated} variant="soft">
          <IconArrowUpRight aria-hidden="true" className="h-4 w-4" />
          {escalated ? 'Escalated' : 'Escalate'}
        </Button>
      }
    >
      <EscalationForm
        context={context}
        onContextChange={setContext}
        onReasonChange={setReason}
        onRouteTeamChange={setRouteTeam}
        reason={reason}
        ready={ready}
        routeTeam={routeTeam}
      />

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={() => setOpen(false)} variant="ghost">
          Keep working
        </Button>
        <Button
          disabled={!canConfirm}
          onClick={() => {
            if (!reason || !routeTeam) return;
            onConfirm({
              reason,
              routeTeam,
              context: context.trim() || undefined,
            });
            setOpen(false);
          }}
          variant="soft"
        >
          Confirm escalation
        </Button>
      </div>
    </Modal>
  );
}
