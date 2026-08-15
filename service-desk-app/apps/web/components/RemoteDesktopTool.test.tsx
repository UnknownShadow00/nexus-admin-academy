import { REMOTE_DESKTOP_SCENARIOS } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  CompletionSummary,
  ProgressiveHints,
} from './RemoteDesktopTool';
import type { RemoteDesktopWorkstationRecord } from './TicketSessionProvider';
import { progressiveHints } from '../lib/remote-desktop-learning';

describe('Remote Desktop assessment hints', () => {
  it('does not render Guided hint text after an Assessment refresh or resume', () => {
    const scenario = REMOTE_DESKTOP_SCENARIOS[0]!;
    const guidedHint = scenario.studentHints[0]!;
    const guidedMarkup = renderToStaticMarkup(
      <ProgressiveHints
        canReveal={false}
        completed={false}
        hints={progressiveHints(scenario, 1, 'guided', false)}
        learningMode="guided"
        onReveal={() => {}}
      />,
    );
    const assessmentMarkup = renderToStaticMarkup(
      <ProgressiveHints
        canReveal={false}
        completed
        // Simulates the persisted Guided reveal count being present after both
        // a browser refresh and a resumed Assessment attempt.
        hints={progressiveHints(scenario, 3, 'assessment', true)}
        learningMode="assessment"
        onReveal={() => {}}
      />,
    );

    expect(guidedMarkup).toContain(guidedHint);
    expect(assessmentMarkup).not.toContain(guidedHint);
    expect(assessmentMarkup).not.toContain(scenario.studentHints[1]!);
    expect(assessmentMarkup).not.toContain(scenario.studentHints[2]!);
  });

  it('renders the final score only from the authoritative server grade', () => {
    const scenario = REMOTE_DESKTOP_SCENARIOS.find(
      (candidate) => candidate.ticketId === 'INC2405',
    )!;
    const markup = renderToStaticMarkup(
      <CompletionSummary
        hintTexts={[]}
        hintsUsed={0}
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
