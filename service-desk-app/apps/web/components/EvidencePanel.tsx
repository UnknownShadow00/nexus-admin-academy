import { Card, CardHeader } from '@service-desk/ui';
import { IconCheck, IconClipboardCheck } from '@tabler/icons-react';
import React from 'react';

import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

export function EvidencePanel({
  workspaceView,
}: {
  workspaceView: NexusWorkspaceView;
}) {
  const needsMoreEvidence = workspaceView.stages.some(
    (stage) =>
      !['understand', 'document'].includes(stage.key) &&
      stage.needs_more_evidence,
  );
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <IconClipboardCheck
              aria-hidden="true"
              className="h-5 w-5 text-accent"
            />
            What you&apos;ve proven
          </span>
        }
      />
      <div className="p-4 sm:p-5">
        <p className="text-xs leading-5 text-text-muted">
          Evidence is recorded automatically when a tool action succeeds. You
          can&apos;t mark it yourself.
        </p>
        {workspaceView.evidence.length ? (
          <ul className="mt-4 space-y-2">
            {workspaceView.evidence.map((item) => (
              <li
                className="flex items-start gap-2 rounded-sm border border-success/20 bg-success/5 p-2.5"
                key={item.id}
              >
                <IconCheck
                  aria-hidden="true"
                  className="mt-0.5 h-4 w-4 shrink-0 text-success"
                />
                <span className="text-sm text-text">
                  {item.label}{' '}
                  <span className="block text-xs font-semibold text-success">
                    Confirmed
                  </span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-text-muted">
            No evidence confirmed yet.
          </p>
        )}
        {needsMoreEvidence ? (
          <p className="mt-3 text-xs text-text-muted">
            Investigation still needs more evidence.
          </p>
        ) : null}
      </div>
    </Card>
  );
}
