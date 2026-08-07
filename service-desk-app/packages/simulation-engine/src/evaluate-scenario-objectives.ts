import {
  getDirectoryUserById,
  type ScenarioActionRule,
  type ScenarioObjective,
  type ScenarioVersion,
} from '@service-desk/shared';

import type { ActionEvent, Attempt } from './types';

export interface ScenarioObjectiveResult {
  description: string;
  earned: number;
  id: string;
  passed: boolean;
  points: number;
  required: boolean;
}

export interface ScenarioActionRuleResult {
  description: string;
  id: string;
  matchedEventId: string | null;
  passed: boolean;
}

export interface ScenarioEvaluationResult {
  forbiddenActions: ScenarioActionRuleResult[];
  hintPenalty: number;
  objectives: ScenarioObjectiveResult[];
  pointsPossible: number;
  requiredActions: ScenarioActionRuleResult[];
  totalScore: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function partialMatch(
  actual: Readonly<Record<string, unknown>>,
  expected: Readonly<Record<string, unknown>>,
): boolean {
  return Object.entries(expected).every(([key, expectedValue]) => {
    const actualValue = actual[key];
    if (isRecord(expectedValue)) {
      return isRecord(actualValue) && partialMatch(actualValue, expectedValue);
    }
    if (Array.isArray(expectedValue)) {
      return (
        Array.isArray(actualValue) &&
        expectedValue.every((item) => actualValue.includes(item))
      );
    }
    return actualValue === expectedValue;
  });
}

export function collectScenarioActionEvents(attempt: Attempt): ActionEvent[] {
  const events = [
    ...Object.values(attempt.ticketOverlays).flatMap(
      (overlay) => overlay.events,
    ),
    ...Object.values(attempt.directoryOverlays).flatMap(
      (overlay) => overlay.events,
    ),
    ...Object.values(attempt.chatThreads).flatMap((overlay) => overlay.events),
    ...Object.values(attempt.assetOverlays).flatMap(
      (overlay) => overlay.events,
    ),
    ...Object.values(attempt.pcShelfOverlays).flatMap(
      (overlay) => overlay.events,
    ),
    ...Object.values(attempt.deploymentRuns).flatMap((run) => run.events),
    ...Object.values(attempt.shipments).flatMap((shipment) => shipment.events),
    ...Object.values(attempt.serverRoomOverlays).flatMap(
      (overlay) => overlay.events,
    ),
    ...Object.values(attempt.remoteDesktopOverlays).flatMap(
      (overlay) => overlay.events,
    ),
  ];

  return [...new Map(events.map((event) => [event.id, event])).values()].sort(
    (left, right) => left.createdAt.localeCompare(right.createdAt),
  );
}

export function scenarioTicketId(version: Pick<ScenarioVersion, 'id'>) {
  return `admin-scenario-ticket:${version.id}`;
}

function matchingEvent(
  events: readonly ActionEvent[],
  actionType: unknown,
  payloadMatch: unknown,
) {
  if (typeof actionType !== 'string') {
    return undefined;
  }
  const expected = isRecord(payloadMatch) ? payloadMatch : {};
  return events.find(
    (event) =>
      event.success &&
      event.type === actionType &&
      partialMatch(event.payload, expected),
  );
}

function effectiveDirectoryGroups(attempt: Attempt, directoryUserId: string) {
  const fixture = getDirectoryUserById(directoryUserId);
  const overlay = attempt.directoryOverlays[directoryUserId];
  const base = fixture?.groups ?? [];
  if (!overlay) {
    return [...base];
  }
  const removed = new Set(overlay.groupChanges.removed);
  const baseSet = new Set<string>(base);
  return [
    ...base.filter((group) => !removed.has(group)),
    ...overlay.groupChanges.added.filter((group) => !baseSet.has(group)),
  ];
}

function objectivePassed(
  objective: ScenarioObjective,
  attempt: Attempt,
  version: ScenarioVersion,
  events: readonly ActionEvent[],
) {
  const params = objective.predicateParams;
  switch (objective.predicateType) {
    case 'action_event_occurred':
      return Boolean(
        matchingEvent(events, params.actionType, params.payloadMatch),
      );
    case 'directory_group_membership': {
      const directoryUserId = params.directoryUserId;
      const group = params.group;
      if (typeof directoryUserId !== 'string' || typeof group !== 'string') {
        return false;
      }
      const includes = effectiveDirectoryGroups(
        attempt,
        directoryUserId,
      ).includes(group);
      return params.includes === false ? !includes : includes;
    }
    case 'directory_user_field': {
      const directoryUserId = params.directoryUserId;
      const field = params.field;
      if (
        typeof directoryUserId !== 'string' ||
        !['locked', 'disabled', 'mfaEnrolled'].includes(String(field))
      ) {
        return false;
      }
      const overlay = attempt.directoryOverlays[directoryUserId];
      const fixture = getDirectoryUserById(directoryUserId);
      const actual =
        overlay?.[field as 'disabled' | 'locked' | 'mfaEnrolled'] ??
        fixture?.[field as 'disabled' | 'locked' | 'mfaEnrolled'];
      return actual === params.equals;
    }
    case 'ticket_verified_resolved':
      return (
        attempt.ticketOverlays[scenarioTicketId(version)]?.closure
          ?.verifiedResolved === true
      );
  }
}

function ruleMatch(
  rule: ScenarioActionRule,
  events: readonly ActionEvent[],
): ActionEvent | undefined {
  return matchingEvent(events, rule.actionType, rule.payloadMatch);
}

export function evaluateScenarioObjectives(
  attempt: Attempt,
  version: ScenarioVersion,
): ScenarioEvaluationResult {
  const events = collectScenarioActionEvents(attempt);
  const objectives = [...version.objectives]
    .sort((left, right) => left.order - right.order)
    .map((objective) => {
      const passed = objectivePassed(objective, attempt, version, events);
      return {
        description: objective.description,
        earned: passed ? objective.pointValue : 0,
        id: objective.id,
        passed,
        points: objective.pointValue,
        required: objective.required,
      };
    });
  const requiredActions = version.requiredActions.map((rule) => {
    const event = ruleMatch(rule, events);
    return {
      description: rule.description,
      id: rule.id,
      matchedEventId: event?.id ?? null,
      passed: Boolean(event),
    };
  });
  const forbiddenActions = version.forbiddenActions.map((rule) => {
    const event = ruleMatch(rule, events);
    return {
      description: rule.description,
      id: rule.id,
      matchedEventId: event?.id ?? null,
      passed: !event,
    };
  });
  const revealedHints =
    attempt.ticketOverlays[scenarioTicketId(version)]?.hintsRevealedCount ?? 0;
  const hintPenalty = [...version.hints]
    .sort((left, right) => left.order - right.order)
    .slice(0, revealedHints)
    .reduce((total, hint) => total + hint.pointPenalty, 0);
  const earnedPoints = objectives.reduce(
    (total, objective) => total + objective.earned,
    0,
  );

  return {
    forbiddenActions,
    hintPenalty,
    objectives,
    pointsPossible: objectives.reduce(
      (total, objective) => total + objective.points,
      0,
    ),
    requiredActions,
    totalScore: Math.max(0, earnedPoints - hintPenalty),
  };
}
