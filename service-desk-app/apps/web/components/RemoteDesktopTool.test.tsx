import { REMOTE_DESKTOP_SCENARIOS } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  CompletionSummary,
  ticketFromSearch,
} from './RemoteDesktopTool';
import type { RemoteDesktopWorkstationRecord } from './TicketSessionProvider';

describe('Remote Desktop workspace integration', () => {
  it.each(['INC2501', 'INC2504', 'INC2505', 'INC2509'])('withholds %s optimistic completion answers until a full server debrief', (ticketId) => {
    const scenario = REMOTE_DESKTOP_SCENARIOS.find((candidate) => candidate.ticketId === ticketId)!;
    const markup = renderToStaticMarkup(<CompletionSummary scenario={scenario} progress={undefined} serverGrade={undefined} workstation={{ scenarioSteps: {} } as RemoteDesktopWorkstationRecord} />);
    expect(markup).not.toContain(scenario.completion.rootCause);
    expect(markup).not.toContain(scenario.completion.whatFixed);
    expect(markup).toContain('being confirmed');
  });
  it('does not silently default to another ticket when context is missing', () => {
    expect(ticketFromSearch('')).toBeNull();
    expect(ticketFromSearch('?ticket=INC2405')).toBe('INC2405');
    expect(ticketFromSearch('?ticket=UNKNOWN')).toBeNull();
  });
  it('renders the final score only from the authoritative server grade', () => {
    const scenario = REMOTE_DESKTOP_SCENARIOS.find(
      (candidate) => candidate.ticketId === 'INC2405',
    )!;
    const markup = renderToStaticMarkup(
      <CompletionSummary
        progress={{
          diagnosisEvidence: [],
          fixEvidence: [],
          investigationEvidence: [],
          internalNote: 'Documented a locally complete workflow.',
          phases: {
            closed: true,
            diagnosed: true,
            fixed: true,
            investigated: true,
            noted: true,
            verified: true,
          },
          verificationEvidence: [],
          // Regression guard: this optimistic local value must not render.
          finalScore: 100,
          feedback: 'Local success',
        }}
        scenario={scenario}
        serverGrade={{
          attempt_id: 1,
          critical_failure: false,
          feedback_summary: 'Server found a missing required evidence item.',
          id: 1,
          overall_score: 40,
          passed: false,
          rubric_version: 'process-v3',
          scenario_version_id: 1,
          technical_complete: false,
        }}
        workstation={{ scenarioSteps: {} } as RemoteDesktopWorkstationRecord}
      />,
    );

    expect(markup).toContain('Server assessment incomplete');
    expect(markup).toContain('40/100');
    expect(markup).not.toContain('100/100');
    expect(markup).not.toContain('Local success');
  });
});
