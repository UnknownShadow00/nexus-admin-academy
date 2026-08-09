import {
  Priority,
  TicketStatus,
  getRemoteDesktopScenarioByTicket,
  type Ticket,
} from '@service-desk/shared';

import type { Attempt, Grade } from './types';

const POINTS_BY_PRIORITY: Readonly<Record<Priority, number>> = {
  // Original Phase 4 scale: urgent work is worth 160, then 120/80/50.
  [Priority.Critical]: 160,
  [Priority.High]: 120,
  [Priority.Medium]: 80,
  [Priority.Low]: 50,
};

const UNRESOLVED_CLOSE_PENALTY_RATE = 0.25;
const HINT_PENALTY_POINTS = 5;
const FREE_HINT_COUNT = 1;
export function evaluateObjectives(
  attempt: Attempt,
  ticketId: string,
  fixtures: readonly Ticket[],
): Grade {
  const fixture = fixtures.find((ticket) => ticket.id === ticketId);
  const overlay = attempt.ticketOverlays[ticketId];
  const pointsPossible = fixture ? POINTS_BY_PRIORITY[fixture.priority] : 0;
  const hintsUsed = overlay?.hintsRevealedCount ?? 0;
  const resolved =
    overlay?.status === TicketStatus.Resolved &&
    overlay.closure?.verifiedResolved === true;
  const wasClosed = overlay?.closure !== null && overlay?.closure !== undefined;
  const unresolvedPenalty =
    wasClosed && !resolved
      ? Math.round(pointsPossible * UNRESOLVED_CLOSE_PENALTY_RATE)
      : 0;
  const hintPenalty =
    wasClosed || resolved
      ? Math.max(0, hintsUsed - FREE_HINT_COUNT) * HINT_PENALTY_POINTS
      : 0;
  const penaltyPoints = unresolvedPenalty + hintPenalty;
  const scenario = getRemoteDesktopScenarioByTicket(ticketId);
  const workflowScore = scenario?.workflow
    ? attempt.remoteDesktopOverlays[scenario.assetTag]?.scenarioProgress[
        scenario.id
      ]?.finalScore
    : null;
  const objectivePoints =
    workflowScore === null || workflowScore === undefined
      ? pointsPossible
      : Math.round((pointsPossible * workflowScore) / 100);
  const pointsBeforePenalty = resolved || wasClosed ? objectivePoints : 0;

  return {
    attemptId: attempt.id,
    ticketId,
    pointsAwarded: Math.max(0, pointsBeforePenalty - penaltyPoints),
    pointsPossible,
    penaltyPoints,
    hintsUsed,
    resolved,
    computedAt: overlay?.closure?.closedAt ?? attempt.startedAt,
  };
}
