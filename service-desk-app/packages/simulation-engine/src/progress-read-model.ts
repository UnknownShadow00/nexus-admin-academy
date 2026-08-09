import {
  ACHIEVEMENT_DEFINITIONS,
  Priority,
  TICKET_FIXTURES,
  TicketCategory,
  getRankForPoints,
  type Achievement,
  type RankProgress,
  type Ticket,
} from '@service-desk/shared';

import type { ActionEvent, Attempt, Grade } from './types';

const FREE_HINT_COUNT = 1;
const HINT_PENALTY_POINTS = 5;

export interface BreakdownItem<T extends string> {
  count: number;
  key: T;
  label: string;
  percentage: number;
}

export interface TicketTimeEntry {
  closedAt: string;
  durationMs: number;
  startedAt: string;
  ticketId: string;
}

export interface AnalyticsSummary {
  accuracyPercent: number;
  actionsPerformed: number;
  categoryBreakdown: readonly BreakdownItem<TicketCategory>[];
  hintPenaltyPoints: number;
  hintsUsed: number;
  pointsPossibleTotal: number;
  pointsTotal: number;
  priorityDistribution: readonly BreakdownItem<Priority>[];
  rank: RankProgress;
  ticketsAttempted: number;
  ticketsResolved: number;
  timeSpentAverageMs: number;
  timeSpentEntries: readonly TicketTimeEntry[];
  timeSpentTicketCount: number;
  timeSpentTotalMs: number;
}

export interface EvaluatedAchievement extends Achievement {
  currentValue: number;
  earned: boolean;
  earnedAt: string | null;
}

export interface PastTicket {
  category: TicketCategory;
  closedAt: string;
  id: string;
  pointsAwarded: number;
  pointsPossible: number;
  priority: Priority;
  resolved: boolean;
  title: string;
}

function toLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function percentage(count: number, total: number) {
  return total === 0 ? 0 : Math.round((count / total) * 1_000) / 10;
}

function validTimestamp(value: string) {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function collectActionEvents(attempt: Attempt): ActionEvent[] {
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

  return [...new Map(events.map((event) => [event.id, event])).values()];
}

function deriveTimeEntries(attempt: Attempt): TicketTimeEntry[] {
  return Object.values(attempt.grades).flatMap((grade) => {
    const overlay = attempt.ticketOverlays[grade.ticketId];
    const closure = overlay?.closure;

    if (!closure || overlay.events.length === 0) {
      return [];
    }

    const closedAtMs = validTimestamp(closure.closedAt);
    const eventTimes = overlay.events
      .map((event) => validTimestamp(event.createdAt))
      .filter((timestamp): timestamp is number => timestamp !== null);

    if (closedAtMs === null || eventTimes.length === 0) {
      return [];
    }

    const startedAtMs = Math.min(...eventTimes);
    if (closedAtMs < startedAtMs) {
      return [];
    }

    return [
      {
        closedAt: closure.closedAt,
        durationMs: closedAtMs - startedAtMs,
        startedAt: new Date(startedAtMs).toISOString(),
        ticketId: grade.ticketId,
      },
    ];
  });
}

export function deriveAnalyticsSummary(
  attempt: Attempt,
  fixtures: readonly Ticket[] = TICKET_FIXTURES,
): AnalyticsSummary {
  const grades = Object.values(attempt.grades);
  const resolvedGrades = grades.filter((grade) => grade.resolved);
  const pointsTotal = grades.reduce(
    (total, grade) => total + grade.pointsAwarded,
    0,
  );
  const pointsPossibleTotal = grades.reduce(
    (total, grade) => total + grade.pointsPossible,
    0,
  );
  const fixtureById = new Map<string, Ticket>(
    fixtures.map((ticket) => [ticket.id, ticket]),
  );
  const categoryKeys = [...new Set(fixtures.map((ticket) => ticket.category))];
  const priorityKeys = Object.values(Priority);
  const timeSpentEntries = deriveTimeEntries(attempt);
  const timeSpentTotalMs = timeSpentEntries.reduce(
    (total, entry) => total + entry.durationMs,
    0,
  );

  return {
    accuracyPercent:
      pointsPossibleTotal === 0
        ? 0
        : Math.round((pointsTotal / pointsPossibleTotal) * 1_000) / 10,
    actionsPerformed: collectActionEvents(attempt).length,
    categoryBreakdown: categoryKeys.map((category) => {
      const count = resolvedGrades.filter(
        (grade) => fixtureById.get(grade.ticketId)?.category === category,
      ).length;
      return {
        count,
        key: category,
        label: toLabel(category),
        percentage: percentage(count, resolvedGrades.length),
      };
    }),
    hintPenaltyPoints: grades.reduce((total, grade) => {
      const calculatedHintPenalty =
        Math.max(0, grade.hintsUsed - FREE_HINT_COUNT) * HINT_PENALTY_POINTS;
      return total + Math.min(grade.penaltyPoints, calculatedHintPenalty);
    }, 0),
    hintsUsed: Object.values(attempt.ticketOverlays).reduce(
      (total, overlay) => total + overlay.hintsRevealedCount,
      0,
    ),
    pointsPossibleTotal,
    pointsTotal,
    priorityDistribution: priorityKeys.map((priority) => {
      const count = resolvedGrades.filter(
        (grade) => fixtureById.get(grade.ticketId)?.priority === priority,
      ).length;
      return {
        count,
        key: priority,
        label: toLabel(priority),
        percentage: percentage(count, resolvedGrades.length),
      };
    }),
    rank: getRankForPoints(pointsTotal),
    ticketsAttempted: grades.length,
    ticketsResolved: resolvedGrades.length,
    timeSpentAverageMs:
      timeSpentEntries.length === 0
        ? 0
        : Math.round(timeSpentTotalMs / timeSpentEntries.length),
    timeSpentEntries,
    timeSpentTicketCount: timeSpentEntries.length,
    timeSpentTotalMs,
  };
}

function sortGradesByDate(grades: readonly Grade[]) {
  return [...grades].sort((left, right) =>
    left.computedAt.localeCompare(right.computedAt),
  );
}

function thresholdDate(grades: readonly Grade[], threshold: number) {
  return sortGradesByDate(grades)[threshold - 1]?.computedAt ?? null;
}

function scoreThresholdDate(grades: readonly Grade[], threshold: number) {
  let runningTotal = 0;

  for (const grade of sortGradesByDate(grades)) {
    runningTotal += grade.pointsAwarded;
    if (runningTotal >= threshold) {
      return grade.computedAt;
    }
  }

  return null;
}

export function evaluateAchievements(
  attempt: Attempt,
  fixtures: readonly Ticket[] = TICKET_FIXTURES,
): EvaluatedAchievement[] {
  const summary = deriveAnalyticsSummary(attempt, fixtures);
  const grades = Object.values(attempt.grades);
  const resolvedGrades = grades.filter((grade) => grade.resolved);
  const fixtureById = new Map<string, Ticket>(
    fixtures.map((ticket) => [ticket.id, ticket]),
  );

  return ACHIEVEMENT_DEFINITIONS.map((definition) => {
    let currentValue: number;
    let earnedAt: string | null;

    switch (definition.thresholdType) {
      case 'tickets_resolved':
        currentValue = resolvedGrades.length;
        earnedAt = thresholdDate(resolvedGrades, definition.threshold);
        break;
      case 'hint_free_resolutions': {
        const qualifying = resolvedGrades.filter(
          (grade) => grade.hintsUsed === 0,
        );
        currentValue = qualifying.length;
        earnedAt = thresholdDate(qualifying, definition.threshold);
        break;
      }
      case 'fast_resolution_seconds': {
        const qualifying = summary.timeSpentEntries
          .filter(
            (entry) =>
              attempt.grades[entry.ticketId]?.resolved === true &&
              entry.durationMs < definition.threshold * 1_000,
          )
          .sort((left, right) => left.closedAt.localeCompare(right.closedAt));
        currentValue = qualifying.length;
        earnedAt = qualifying[0]
          ? (attempt.grades[qualifying[0].ticketId]?.computedAt ?? null)
          : null;
        break;
      }
      case 'accuracy_percent':
        currentValue = summary.accuracyPercent;
        earnedAt =
          grades.length > 0 && currentValue >= definition.threshold
            ? (sortGradesByDate(grades).at(-1)?.computedAt ?? null)
            : null;
        break;
      case 'score_points':
        currentValue = summary.pointsTotal;
        earnedAt = scoreThresholdDate(grades, definition.threshold);
        break;
      default: {
        const category = definition.thresholdType.split(
          ':',
        )[1] as TicketCategory;
        const qualifying = resolvedGrades.filter(
          (grade) => fixtureById.get(grade.ticketId)?.category === category,
        );
        currentValue = qualifying.length;
        earnedAt = thresholdDate(qualifying, definition.threshold);
      }
    }

    return {
      ...definition,
      currentValue,
      earned: earnedAt !== null,
      earnedAt,
    };
  });
}

export function derivePastTickets(
  attempt: Attempt,
  fixtures: readonly Ticket[] = TICKET_FIXTURES,
): PastTicket[] {
  const fixtureById = new Map<string, Ticket>(
    fixtures.map((ticket) => [ticket.id, ticket]),
  );

  return Object.values(attempt.grades)
    .flatMap((grade) => {
      const fixture = fixtureById.get(grade.ticketId);
      if (!fixture) {
        return [];
      }

      return [
        {
          category: fixture.category,
          closedAt: grade.computedAt,
          id: fixture.id,
          pointsAwarded: grade.pointsAwarded,
          pointsPossible: grade.pointsPossible,
          priority: fixture.priority,
          resolved: grade.resolved,
          title: fixture.title,
        },
      ];
    })
    .sort((left, right) => right.closedAt.localeCompare(left.closedAt));
}
