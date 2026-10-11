import { describe, expect, it } from 'vitest';
import type { NexusGrade } from './nexus-service-desk-client';
import {
  learnerOutcomeCopy,
  pendingResultCopy,
  resultExperienceMode,
} from './ticket-result-presentation';

const grade: NexusGrade = {
  attempt_id: 12,
  id: 1,
  passed: true,
  overall_score: 100,
  critical_failure: false,
  technical_complete: true,
  feedback_summary: 'Server feedback',
  rubric_version: 'server-process-v3',
  scenario_version_id: 1,
};

describe('server-owned ticket result presentation', () => {
  it.each([
    [
      'guided',
      'Guided practice result',
      'check Academy for activity progress.',
    ],
    ['practice', 'Practice result', 'no assessment credit or mastery XP.'],
    ['assessment', 'Assessment result', 'check Academy for awarded credit.'],
  ] as const)(
    'distinguishes every %s result state without awarding anything',
    (mode, label, credit) => {
      expect(learnerOutcomeCopy(grade, mode)).toBe(
        `${label}: PASS — ${credit}`,
      );
      expect(
        learnerOutcomeCopy(
          { ...grade, learner_outcome: 'escalated_successfully' },
          mode,
        ),
      ).toBe(`${label}: ESCALATED SUCCESSFULLY — ${credit}`);
      // A numeric score, operational closure or escalation alone cannot pass a failed grade.
      expect(
        learnerOutcomeCopy(
          {
            ...grade,
            passed: false,
            learner_outcome: 'escalated_successfully',
          },
          mode,
        ),
      ).toBe(`${label}: NEEDS ANOTHER ATTEMPT — no pass for this attempt.`);
      expect(
        learnerOutcomeCopy(
          { ...grade, passed: false, learner_outcome: 'awaiting_review' },
          mode,
        ),
      ).toBe(`${label}: AWAITING REVIEW — no final result yet.`);
      expect(
        learnerOutcomeCopy(
          { ...grade, passed: true, learner_outcome: 'awaiting_review' },
          mode,
        ),
      ).toBe(`${label}: AWAITING REVIEW — no final result yet.`);
      expect(pendingResultCopy(mode)).toBe(
        `${label}: AWAITING SERVER RESULT — not yet graded.`,
      );
    },
  );

  it('uses the matching graded attempt rather than guessing from the assignment', () => {
    expect(
      resultExperienceMode(grade, { id: 12, experience_mode: 'assessment' }),
    ).toBe('assessment');
    expect(
      resultExperienceMode(grade, { id: '12', experience_mode: 'practice' }),
    ).toBe('practice');
    expect(
      resultExperienceMode(grade, { id: 13, experience_mode: 'practice' }),
    ).toBeUndefined();
    expect(resultExperienceMode(grade, undefined)).toBeUndefined();
    expect(learnerOutcomeCopy(grade)).toBe(
      'Ticket result: PASS — credit not confirmed.',
    );
    expect(pendingResultCopy()).not.toContain('AWAITING REVIEW');
  });

  it('does not compute rewards or mutate server grade while formatting', () => {
    const original = JSON.stringify(grade);
    learnerOutcomeCopy(Object.freeze(grade), 'practice');
    expect(JSON.stringify(grade)).toBe(original);
    expect(
      learnerOutcomeCopy(
        { ...grade, passed: false, overall_score: 100 },
        'assessment',
      ),
    ).not.toContain('credit confirmed');
  });
});
