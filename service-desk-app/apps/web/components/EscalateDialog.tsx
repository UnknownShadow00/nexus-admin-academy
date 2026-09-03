'use client';

import {
  ESCALATION_REASONS,
  ESCALATION_REASON_DESCRIPTIONS,
  ESCALATION_REASON_LABELS,
  type EscalationReason,
} from '@service-desk/shared';
import { Button, Modal } from '@service-desk/ui';
import { IconArrowUpRight, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';

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

export function EscalateDialog({
  escalated,
  workspaceView,
  onConfirm,
}: EscalateDialogProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<EscalationReason | ''>('');
  const [context, setContext] = useState('');

  const route = workspaceView?.escalation?.route ?? null;
  const ready = investigationReady(workspaceView);
  const canConfirm = Boolean(reason) && Boolean(route) && ready && !escalated;

  return (
    <Modal
      description="Route this incident to the team that owns it."
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
      {route ? (
        <p className="rounded-sm border border-border bg-surface-muted p-3 text-sm text-text">
          This will be routed to:{' '}
          <span className="font-bold text-text">{route}</span>
        </p>
      ) : (
        <p className="rounded-sm border border-border bg-surface-muted p-3 text-sm text-text-muted">
          A destination team has not been configured for this ticket.
        </p>
      )}

      {!ready ? (
        <div className="mt-4 flex gap-2 rounded-sm border border-warning/40 bg-warning/10 p-3 text-sm text-text">
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

      <label className="mt-4 block text-sm font-bold text-text">
        Reason for escalation
        <select
          className="sd-focus-ring mt-2 w-full rounded-sm border border-border bg-surface p-2 text-sm text-text"
          onChange={(event) =>
            setReason(event.target.value as EscalationReason | '')
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
      </label>
      {reason ? (
        <p className="mt-1 text-xs text-text-muted">
          {ESCALATION_REASON_DESCRIPTIONS[reason]}
        </p>
      ) : null}

      <label className="mt-4 block text-sm font-bold text-text">
        Context for the receiving team{' '}
        <span className="font-normal text-text-muted">(optional)</span>
        <textarea
          className="sd-focus-ring mt-2 min-h-20 w-full rounded-sm border border-border bg-surface p-2 text-sm font-normal text-text"
          maxLength={1000}
          onChange={(event) => setContext(event.target.value)}
          placeholder="What you found and why this needs another team."
          value={context}
        />
      </label>

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={() => setOpen(false)} variant="ghost">
          Keep working
        </Button>
        <Button
          disabled={!canConfirm}
          onClick={() => {
            if (!reason || !route) return;
            onConfirm({
              reason,
              routeTeam: route,
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
