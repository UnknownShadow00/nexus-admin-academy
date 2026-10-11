import { describe, expect, it } from 'vitest';
import type { NexusGrade } from './nexus-service-desk-client';
import {
  learnerOutcomeCopy,
  pendingResultCopy,
  resultExperienceMode,
  resultTicketStatus,
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

  it.each(['open', 'in-progress', 'pending', 'resolved', 'closed'] as const)(
    'restores stored %s independently of pass, fail or pending review',
    (status) => {
      const attempt = {
        id: 12,
        experience_mode: 'practice' as const,
        current_state: {
          nexus_service_desk_attempt: {
            ticketOverlays: {
              INC2501: { status },
              INC2504: { status: 'open' },
            },
          },
        },
      };
      for (const passed of [true, false]) {
        expect(
          resultTicketStatus({ ...grade, passed }, attempt, 'INC2501'),
        ).toBe(status);
        expect(
          resultTicketStatus(
            { ...grade, passed, learner_outcome: 'awaiting_review' },
            attempt,
            'INC2501',
          ),
        ).toBe(status);
      }
      expect(resultTicketStatus(grade, attempt, 'INC2504')).toBe('open');
      expect(resultTicketStatus(grade, attempt, 'INC9999')).toBeUndefined();
    },
  );

  it('does not guess status from grades, a different attempt or malformed snapshots', () => {
    expect(resultTicketStatus(grade, undefined, 'INC2501')).toBeUndefined();
    expect(
      resultTicketStatus(
        grade,
        { id: 12, experience_mode: 'assessment' },
        'INC2501',
      ),
    ).toBeUndefined();
    for (const current_state of [
      {},
      { nexus_service_desk_attempt: null },
      {
        nexus_service_desk_attempt: {
          ticketOverlays: { INC2501: { status: 'PASS' } },
        },
      },
      {
        nexus_service_desk_attempt: {
          ticketOverlays: { INC2501: { status: {} } },
        },
      },
    ]) {
      expect(
        resultTicketStatus(
          grade,
          { id: 12, experience_mode: 'assessment', current_state },
          'INC2501',
        ),
      ).toBeUndefined();
    }
    expect(
      resultTicketStatus(
        grade,
        {
          id: 13,
          experience_mode: 'practice',
          current_state: { status: 'resolved' },
        },
        'INC2501',
      ),
    ).toBeUndefined();
    expect(
      resultTicketStatus(
        grade,
        {
          id: 12,
          experience_mode: 'assessment',
          current_state: { status: 'pending' },
        },
        'INC2501',
      ),
    ).toBe('pending');
  });
});
