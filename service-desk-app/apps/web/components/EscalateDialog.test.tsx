import {
  ESCALATION_REASONS,
  ESCALATION_REASON_LABELS,
  ESCALATION_ROUTES,
} from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { EscalationForm, investigationReady } from './EscalateDialog';
import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

function form(overrides: Partial<Parameters<typeof EscalationForm>[0]> = {}) {
  return renderToStaticMarkup(
    <EscalationForm
      context=""
      onContextChange={() => {}}
      onReasonChange={() => {}}
      onRouteTeamChange={() => {}}
      reason=""
      ready
      routeTeam=""
      {...overrides}
    />,
  );
}

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
    escalation: { available: true },
    evidence: [],
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

  it('never announces a destination before the student chooses one', () => {
    const markup = form();
    // Fix 2: the pre-decision form carries no server-chosen route and no
    // wording that implies escalation is the correct outcome here.
    expect(markup).not.toContain('This will be routed');
    expect(markup).not.toContain('will be routed to');
    expect(markup).toContain('Choose a team…');
    // The only pre-selected option is the empty placeholder: no team is
    // pre-picked, so the markup cannot hint at the correct destination.
    expect(markup.match(/selected=""/g)).toHaveLength(2);
    expect(markup).toContain('<option value="" selected="">Choose a reason…');
    expect(markup).toContain('<option value="" selected="">Choose a team…');
    expect(markup).toContain('Nexus checks your choice after you submit.');
  });

  it('lets the student pick any supported destination team', () => {
    const markup = form();
    for (const route of ESCALATION_ROUTES) {
      expect(markup).toContain(route.replace(/&/g, '&amp;'));
    }
    expect(ESCALATION_ROUTES).toContain('Other / Mentor Review');
  });

  it('associates both selectors with explicit labels', () => {
    const markup = form({ reason: 'security-incident' });
    // Fix 9: label htmlFor + matching id on reason AND destination.
    expect(markup).toContain('for="escalate-reason"');
    expect(markup).toContain('id="escalate-reason"');
    expect(markup).toContain('for="escalate-destination"');
    expect(markup).toContain('id="escalate-destination"');
    expect(markup).toContain('aria-describedby="escalate-reason-help"');
    expect(markup).toContain('aria-describedby="escalate-destination-help"');
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
