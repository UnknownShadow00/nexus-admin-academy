import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  FACILITIES_CALENDAR_GROUP,
  TicketStatus,
  type ScenarioVersion,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import { createAttempt } from './attempt';
import {
  evaluateScenarioObjectives,
  scenarioTicketId,
} from './evaluate-scenario-objectives';
import type { ActionEvent, Attempt } from './types';

function version(): ScenarioVersion {
  return {
    description: {
      businessImpact: 'Blocked',
      issue: 'Access denied',
      reportedByLine: 'Portal',
      troubleshooting: [],
    },
    device: {
      assetTag: 'NX-1',
      deviceName: 'Laptop',
      kind: 'laptop',
      operatingSystem: 'Windows 11',
      state: 'active',
    },
    difficulty: 'easy',
    explanation: 'Unlock and verify.',
    forbiddenActions: [
      {
        actionType: 'directory.disable_account',
        description: 'Do not disable the requester.',
        id: 'forbidden-1',
      },
    ],
    hints: [],
    id: 'version-1',
    initialWorldState: {
      assetOverlaySeeds: {},
      chatMessageSeeds: [],
      directoryOverlaySeeds: {},
    },
    objectives: [
      {
        description: 'Unlock event',
        id: 'o1',
        order: 1,
        pointValue: 10,
        predicateParams: {
          actionType: 'directory.unlock_account',
          payloadMatch: {
            directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
          },
        },
        predicateType: 'action_event_occurred',
        required: true,
      },
      {
        description: 'Calendar membership',
        id: 'o2',
        order: 2,
        pointValue: 20,
        predicateParams: {
          directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
          group: FACILITIES_CALENDAR_GROUP,
          includes: true,
        },
        predicateType: 'directory_group_membership',
        required: true,
      },
      {
        description: 'Unlocked state',
        id: 'o3',
        order: 3,
        pointValue: 30,
        predicateParams: {
          directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
          equals: false,
          field: 'locked',
        },
        predicateType: 'directory_user_field',
        required: true,
      },
      {
        description: 'Verified close',
        id: 'o4',
        order: 4,
        pointValue: 40,
        predicateParams: {},
        predicateType: 'ticket_verified_resolved',
        required: true,
      },
    ],
    pointValue: 100,
    publishedAt: '2026-07-29T00:00:00.000Z',
    requester: {
      contact: '555',
      department: 'Finance',
      email: 'a@example.test',
      location: 'HQ',
      name: 'Avery',
    },
    requiredActions: [
      {
        actionType: 'ticket.close',
        description: 'Close the ticket.',
        id: 'required-1',
      },
    ],
    scenarioId: 'scenario-1',
    sla: { dueAt: '2026-07-30T00:00:00.000Z', target: '4 hours' },
    version: 1,
  };
}

function event(id: string, type: string, payload: Record<string, unknown>) {
  return {
    actorId: 'test-student',
    attemptId: 'attempt-1',
    createdAt: `2026-07-29T00:00:0${id}.000Z`,
    id,
    payload,
    rejectReason: null,
    success: true,
    type,
  } satisfies ActionEvent;
}

function completedAttempt(scenario: ScenarioVersion): Attempt {
  const base = createAttempt({
    id: 'attempt-1',
    startedAt: '2026-07-29T00:00:00.000Z',
  });
  const unlock = event('1', 'directory.unlock_account', {
    directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
  });
  const close = event('2', 'ticket.close', {
    ticketId: scenarioTicketId(scenario),
  });
  return {
    ...base,
    directoryOverlays: {
      [AVERY_BROOKS_DIRECTORY_USER_ID]: {
        disabled: false,
        events: [unlock],
        groupChanges: {
          added: [FACILITIES_CALENDAR_GROUP],
          removed: [],
        },
        locked: false,
        mfaEnrolled: true,
        passwordState: 'current',
        mfaFactorStatus: 'available',
        inspected: false,
        identityVerified: false,
        identityVerificationMethod: null,
        primaryAuthTested: false,
        diagnosis: null,
        accessVerified: false,
      },
    },
    ticketOverlays: {
      [scenarioTicketId(scenario)]: {
        assignedTo: 'you',
        closure: {
          closedAt: close.createdAt,
          resolutionNote: 'Verified',
          verifiedResolved: true,
        },
        escalated: false,
        events: [close],
        hintsRevealedCount: 0,
        notes: [],
        status: TicketStatus.Resolved,
      },
    },
  };
}

describe('generic scenario objective evaluation', () => {
  it('evaluates action_event_occurred with a partial payload match', () => {
    const scenario = version();
    const result = evaluateScenarioObjectives(
      completedAttempt(scenario),
      scenario,
    );

    expect(result.objectives.find((item) => item.id === 'o1')).toMatchObject({
      earned: 10,
      passed: true,
    });
    expect(result.requiredActions[0]?.passed).toBe(true);
  });

  it('evaluates directory_group_membership against effective groups', () => {
    const scenario = version();
    const result = evaluateScenarioObjectives(
      completedAttempt(scenario),
      scenario,
    );

    expect(result.objectives.find((item) => item.id === 'o2')).toMatchObject({
      earned: 20,
      passed: true,
    });
  });

  it('evaluates directory_user_field against overlay state', () => {
    const scenario = version();
    const result = evaluateScenarioObjectives(
      completedAttempt(scenario),
      scenario,
    );

    expect(result.objectives.find((item) => item.id === 'o3')).toMatchObject({
      earned: 30,
      passed: true,
    });
  });

  it('evaluates ticket_verified_resolved against the synthetic closure', () => {
    const scenario = version();
    const result = evaluateScenarioObjectives(
      completedAttempt(scenario),
      scenario,
    );

    expect(result.objectives.find((item) => item.id === 'o4')).toMatchObject({
      earned: 40,
      passed: true,
    });
    expect(result.totalScore).toBe(100);
    expect(result.pointsPossible).toBe(100);
  });

  it('reports a successful forbidden action as a violation', () => {
    const scenario = version();
    const attempt = completedAttempt(scenario);
    const forbidden = event('3', 'directory.disable_account', {
      directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
    });
    const withViolation: Attempt = {
      ...attempt,
      directoryOverlays: {
        ...attempt.directoryOverlays,
        [AVERY_BROOKS_DIRECTORY_USER_ID]: {
          ...attempt.directoryOverlays[AVERY_BROOKS_DIRECTORY_USER_ID]!,
          events: [
            ...attempt.directoryOverlays[AVERY_BROOKS_DIRECTORY_USER_ID]!
              .events,
            forbidden,
          ],
        },
      },
    };

    expect(
      evaluateScenarioObjectives(withViolation, scenario).forbiddenActions[0],
    ).toMatchObject({ matchedEventId: '3', passed: false });
  });
});
