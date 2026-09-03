import {
  ESCALATION_REASONS,
  ESCALATION_REASON_LABELS,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import { investigationReady } from './EscalateDialog';
import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

function view(
  stageStatuses: Partial<Record<string, NexusWorkspaceView['stages'][number]['status']>>,
): NexusWorkspaceView {
  const keys = [
    'understand',
    'investigate',
    'diagnose',
    'fix',
    'verify',
    'document',
  ] as const;
  return {
    documentation_target: 'remote_desktop',
    escalation: { available: true, route: 'Identity & Access' },
    evidence: [],
    resolve_blockers: [],
    stages: keys.map((key) => ({
      key,
      status: stageStatuses[key] ?? 'not_started',
    })),
  };
}

describe('EscalateDialog eligibility', () => {
  it('is not ready until investigation and diagnosis are both complete', () => {
    expect(
      investigationReady(view({ investigate: 'complete', diagnose: 'current' })),
    ).toBe(false);
    expect(
      investigationReady(
        view({ investigate: 'current', diagnose: 'not_started' }),
      ),
    ).toBe(false);
  });

  it('is ready once investigation and diagnosis are complete', () => {
    expect(
      investigationReady(
        view({ investigate: 'complete', diagnose: 'complete' }),
      ),
    ).toBe(true);
  });

  it('does not block escalation before the workspace view has loaded', () => {
    expect(investigationReady(null)).toBe(true);
    expect(investigationReady(undefined)).toBe(true);
  });

  it('mirrors the full backend escalation reason taxonomy', () => {
    expect([...ESCALATION_REASONS].sort()).toEqual(
      [
        'change-approval-required',
        'hardware-replacement',
        'other-team-owns-system',
        'permissions-access',
        'policy-authorization',
        'security-incident',
        'unknown-root-cause',
      ].sort(),
    );
    for (const reason of ESCALATION_REASONS) {
      expect(ESCALATION_REASON_LABELS[reason]).toBeTruthy();
    }
  });
});
