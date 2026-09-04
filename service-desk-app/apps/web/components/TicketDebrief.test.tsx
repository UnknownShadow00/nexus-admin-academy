import { describe, expect, it } from 'vitest';

import { canRetryAttempt } from './TicketDebrief';
import type {
  NexusDebrief,
  NexusGrade,
} from '../lib/nexus-service-desk-client';

function debrief(
  attemptsRemaining: number | null,
  tier: NexusDebrief['coaching_tier'] = 'limited',
): NexusDebrief {
  return {
    coaching_tier: tier,
    result: {
      attempts_remaining: attemptsRemaining,
      outcome: 'needs_another_try',
      passed: false,
      score: 20,
    },
    categories: [],
    student_note: '',
    note_dimensions: { action: false, cause: false, verification: false },
    stronger_path: [],
    escalation_feedback: null,
  };
}

function grade(passed: boolean, value: NexusDebrief | null): NexusGrade {
  return {
    attempt_id: 1,
    critical_failure: false,
    debrief: value,
    feedback_summary: 'summary',
    id: 2,
    overall_score: 20,
    passed,
    rubric_version: 'server-process-v3',
    scenario_version_id: 3,
    technical_complete: passed,
  };
}

describe('retry eligibility after a graded attempt', () => {
  it('offers a retry when the attempt failed and the server has attempts left', () => {
    expect(canRetryAttempt(grade(false, debrief(2)), debrief(2))).toBe(true);
    expect(canRetryAttempt(grade(false, debrief(1)), debrief(1))).toBe(true);
  });

  it('offers a retry when the assignment has no attempt ceiling', () => {
    expect(canRetryAttempt(grade(false, debrief(null)), debrief(null))).toBe(
      true,
    );
  });

  it('hides the retry once the final attempt has been used', () => {
    expect(canRetryAttempt(grade(false, debrief(0)), debrief(0))).toBe(false);
  });

  it('never offers a retry for a passing attempt', () => {
    const passing = debrief(2, 'full');
    expect(canRetryAttempt(grade(true, passing), passing)).toBe(false);
  });

  it('does not guess when the server sent no debrief', () => {
    expect(canRetryAttempt(grade(false, null), null)).toBe(false);
  });
});
