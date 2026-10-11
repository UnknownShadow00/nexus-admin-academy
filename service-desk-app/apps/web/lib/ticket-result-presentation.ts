import type { NexusAttempt, NexusGrade } from './nexus-service-desk-client';

export type ResultAttempt = Pick<NexusAttempt, 'id' | 'experience_mode'>;
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
