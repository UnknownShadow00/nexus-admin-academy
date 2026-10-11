import { TicketStatus } from '@service-desk/shared';
import type { NexusAttempt, NexusGrade } from './nexus-service-desk-client';

export type ResultAttempt = Pick<NexusAttempt, 'id' | 'experience_mode'> &
  Partial<Pick<NexusAttempt, 'current_state'>>;
export type ExperienceMode = NexusAttempt['experience_mode'];

/** Use the graded attempt, never the assignment's next launch mode. */
export function resultExperienceMode(
  grade: NexusGrade,
  attempt: ResultAttempt | undefined,
): ExperienceMode | undefined {
  return attempt && String(attempt.id) === String(grade.attempt_id)
    ? attempt.experience_mode
    : undefined;
}

function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

/** Restore the matching server attempt's operational status, never infer it from a grade. */
export function resultTicketStatus(
  grade: NexusGrade,
  attempt: ResultAttempt | undefined,
  ticketId: string,
): TicketStatus | undefined {
  if (!attempt || String(attempt.id) !== String(grade.attempt_id)) return;
  const state = record(attempt.current_state);
  const snapshot = record(state?.nexus_service_desk_attempt);
  const overlays = record(snapshot?.ticketOverlays);
  const overlay = record(overlays?.[ticketId]);
  // Older API attempts stored the ticket overlay directly rather than a full snapshot.
  const status =
    overlay?.status ??
    (state?.nexus_service_desk_attempt === undefined
      ? state?.status
      : undefined);
  return typeof status === 'string' &&
    Object.values(TicketStatus).includes(status as TicketStatus)
    ? (status as TicketStatus)
    : undefined;
}
function resultLabel(mode?: ExperienceMode): string {
  return mode === 'guided'
    ? 'Guided practice result'
    : mode === 'practice'
      ? 'Practice result'
      : mode === 'assessment'
        ? 'Assessment result'
        : 'Ticket result';
}
/** Presentation only: no XP, mastery or curriculum progression is calculated here. */
export function learnerOutcomeCopy(
  grade: NexusGrade,
  mode?: ExperienceMode,
): string {
  const label = resultLabel(mode);
  if (grade.learner_outcome === 'awaiting_review')
    return `${label}: AWAITING REVIEW — no final result yet.`;
  if (!grade.passed)
    return `${label}: NEEDS ANOTHER ATTEMPT — no pass for this attempt.`;
  const outcome =
    grade.learner_outcome === 'escalated_successfully' ||
    grade.debrief?.result.outcome === 'escalated'
      ? 'ESCALATED SUCCESSFULLY'
      : 'PASS';
  const credit =
    mode === 'practice'
      ? 'no assessment credit or mastery XP.'
      : mode === 'guided'
        ? 'check Academy for activity progress.'
        : mode === 'assessment'
          ? 'check Academy for awarded credit.'
          : 'credit not confirmed.';
  return `${label}: ${outcome} — ${credit}`;
}
/** A local closure awaiting the API is not evidence of a mentor-review queue. */
export function pendingResultCopy(mode?: ExperienceMode): string {
  return `${resultLabel(mode)}: AWAITING SERVER RESULT — not yet graded.`;
}
