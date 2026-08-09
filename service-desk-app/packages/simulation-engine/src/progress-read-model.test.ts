import {
  Priority,
  TICKET_FIXTURES,
  TicketCategory,
  TicketStatus,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import { createAttempt } from './attempt';
import {
  deriveAnalyticsSummary,
  derivePastTickets,
  evaluateAchievements,
} from './progress-read-model';
import type { ActionEvent, Attempt, Grade, TicketOverlay } from './types';

function event(id: string, ticketId: string, createdAt: string): ActionEvent {
  return {
    actorId: 'student-you',
    attemptId: 'progress-test',
    createdAt,
    id,
    payload: { ticketId },
    rejectReason: null,
    success: true,
    type: 'ticket.close',
  };
}

function grade(
  ticketId: string,
  computedAt: string,
  options: Partial<Grade> = {},
): Grade {
  return {
    attemptId: 'progress-test',
    computedAt,
    hintsUsed: 0,
    penaltyPoints: 0,
    pointsAwarded: 120,
    pointsPossible: 120,
    resolved: true,
    ticketId,
    ...options,
  };
}

function overlay(
  ticketId: string,
  startedAt: string,
  closedAt: string,
  hintsRevealedCount = 0,
): TicketOverlay {
  return {
    assignedTo: 'you',
    closure: {
      closedAt,
      resolutionNote: 'Resolved in the simulation.',
      verifiedResolved: true,
    },
    escalated: false,
    events: [event(`${ticketId}-start`, ticketId, startedAt)],
    hintsRevealedCount,
    notes: [],
    status: TicketStatus.Resolved,
  };
}

function attemptWithProgress(): Attempt {
  const base = createAttempt({
    id: 'progress-test',
    startedAt: '2026-07-28T10:00:00.000Z',
  });

  return {
    ...base,
    grades: {
      INC2401: grade('INC2401', '2026-07-28T10:01:30.000Z'),
      INC2405: grade('INC2405', '2026-07-28T10:04:00.000Z', {
        hintsUsed: 2,
        penaltyPoints: 5,
        pointsAwarded: 45,
        pointsPossible: 50,
      }),
    },
    ticketOverlays: {
      INC2401: overlay(
        'INC2401',
        '2026-07-28T10:00:00.000Z',
        '2026-07-28T10:01:30.000Z',
      ),
      INC2405: overlay(
        'INC2405',
        '2026-07-28T10:02:00.000Z',
        '2026-07-28T10:04:00.000Z',
        2,
      ),
    },
  };
}

describe('progress read model', () => {
  it('derives score, accuracy, breakdowns, hints, actions, and timing', () => {
    const summary = deriveAnalyticsSummary(attemptWithProgress());

    expect(summary).toMatchObject({
      pointsTotal: 165,
      pointsPossibleTotal: 170,
      accuracyPercent: 97.1,
      ticketsAttempted: 2,
      ticketsResolved: 2,
      actionsPerformed: 2,
      hintsUsed: 2,
      hintPenaltyPoints: 5,
      timeSpentTotalMs: 210_000,
      timeSpentAverageMs: 105_000,
      timeSpentTicketCount: 2,
    });
    expect(
      summary.categoryBreakdown.find(
        (item) => item.key === TicketCategory.Access,
      ),
    ).toMatchObject({ count: 2, percentage: 100 });
    expect(
      summary.priorityDistribution.find((item) => item.key === Priority.High),
    ).toMatchObject({ count: 1, percentage: 50 });
  });

  it('omits timing when a closed ticket has no recorded ticket event', () => {
    const attempt = attemptWithProgress();
    const withoutEvents = {
      ...attempt,
      ticketOverlays: {
        ...attempt.ticketOverlays,
        INC2401: { ...attempt.ticketOverlays.INC2401!, events: [] },
      },
    } satisfies Attempt;

    expect(deriveAnalyticsSummary(withoutEvents).timeSpentTicketCount).toBe(1);
  });

  it('evaluates only achievements supported by grades and ticket timing', () => {
    const achievements = evaluateAchievements(attemptWithProgress());
    const byCode = Object.fromEntries(
      achievements.map((achievement) => [achievement.code, achievement]),
    );

    expect(byCode['first-ticket']!).toMatchObject({
      earned: true,
      earnedAt: '2026-07-28T10:01:30.000Z',
    });
    expect(byCode['self-sufficient']!.earned).toBe(true);
    expect(byCode['speed-demon']!.earned).toBe(true);
    expect(byCode['sharpshooter']!.earned).toBe(true);
    expect(byCode['access-specialist']!).toMatchObject({
      earned: true,
      earnedAt: '2026-07-28T10:04:00.000Z',
    });
    expect(byCode['getting-started']!.earned).toBe(false);
    expect(byCode['score-250']!.earned).toBe(false);
  });

  it('keeps all achievements locked and all rollups at zero for a new attempt', () => {
    const attempt = createAttempt({ id: 'empty-attempt' });

    expect(evaluateAchievements(attempt).every((item) => !item.earned)).toBe(
      true,
    );
    expect(deriveAnalyticsSummary(attempt)).toMatchObject({
      accuracyPercent: 0,
      actionsPerformed: 0,
      pointsTotal: 0,
      ticketsResolved: 0,
      timeSpentAverageMs: 0,
    });
    expect(derivePastTickets(attempt)).toEqual([]);
  });

  it('projects past tickets directly from grades and fixture metadata', () => {
    expect(derivePastTickets(attemptWithProgress())[0]).toMatchObject({
      category: TicketCategory.Access,
      id: 'INC2405',
      pointsAwarded: 45,
      priority: Priority.Low,
      resolved: true,
      title: TICKET_FIXTURES[4].title,
    });
  });
});
