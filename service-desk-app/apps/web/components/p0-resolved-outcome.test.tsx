import { getFixtureTicket, TicketStatus } from '@service-desk/shared';
import React, { Fragment } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { TicketDebrief } from './TicketDebrief';
import { TicketDetailHeader } from './TicketDetailHeader';
import type { NexusGrade } from '../lib/nexus-service-desk-client';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
}));

describe('P0 Finding E — operationally resolved is not assessment passed', () => {
  it.fails(
    'labels the failed learner outcome separately from RESOLVED (fixed in Wave 6)',
    () => {
      const fixture = getFixtureTicket('INC2403');
      if (!fixture) throw new Error('INC2403 fixture is required');
      const ticket = { ...fixture, status: TicketStatus.Resolved };
      const grade: NexusGrade = {
        attempt_id: 1,
        critical_failure: false,
        debrief: {
          coaching_tier: 'limited',
          result: {
            attempts_remaining: 2,
            outcome: 'needs_another_try',
            passed: false,
            score: 0,
          },
          categories: [],
          student_note: '',
          note_dimensions: { action: false, cause: false, verification: false },
          stronger_path: [],
          escalation_feedback: null,
        },
        feedback_summary:
          'The ticket is operationally resolved, but the assessment failed.',
        id: 2,
        overall_score: 0,
        passed: false,
        rubric_version: 'server-process-v3',
        scenario_version_id: 3,
        technical_complete: false,
      };
      const markup = renderToStaticMarkup(
        <Fragment>
          <TicketDetailHeader ticket={ticket} />
          <TicketDebrief grade={grade} ticket={ticket} />
        </Fragment>,
      );

      expect(grade.passed).toBe(false);
      expect(grade.overall_score).toBe(0);
      expect(markup).toContain('Resolved');
      // Current copy says "Needs another try" while the green RESOLVED badge
      // dominates. Wave 6 introduces the unambiguous learner-outcome wording.
      expect(markup).toContain('Needs another attempt');
    },
  );
});
