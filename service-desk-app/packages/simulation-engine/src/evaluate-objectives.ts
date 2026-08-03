import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  FACILITIES_CALENDAR_GROUP,
  Priority,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
  TicketStatus,
  getDirectoryUserById,
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
const DIRECTORY_OBJECTIVE_REDUCED_RATE = 0.5;

function effectiveDirectoryGroups(attempt: Attempt, directoryUserId: string) {
  const fixture = getDirectoryUserById(directoryUserId);
  const overlay = attempt.directoryOverlays[directoryUserId];

  if (!fixture) {
    return [];
  }
  if (!overlay) {
    return [...fixture.groups];
  }

  const removed = new Set(overlay.groupChanges.removed);
  const templateGroups = new Set<string>(fixture.groups);
  return [
    ...fixture.groups.filter((group) => !removed.has(group)),
    ...overlay.groupChanges.added.filter((group) => !templateGroups.has(group)),
  ];
}

function directoryObjectiveSatisfied(attempt: Attempt, ticketId: string) {
  if (ticketId === 'INC2401') {
    const overlay = attempt.directoryOverlays[AVERY_BROOKS_DIRECTORY_USER_ID];

    // Either corrective identity action resolves the simulated auth loop.
    return overlay?.locked === false || overlay?.mfaEnrolled === false;
  }

  if (ticketId === 'INC2405') {
    return effectiveDirectoryGroups(
      attempt,
      SLOANE_RIVERA_DIRECTORY_USER_ID,
    ).includes(FACILITIES_CALENDAR_GROUP);
  }

  return true;
}

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
  const objectivePoints = directoryObjectiveSatisfied(attempt, ticketId)
    ? pointsPossible
    : Math.round(pointsPossible * DIRECTORY_OBJECTIVE_REDUCED_RATE);
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
