import { Link } from "react-router-dom";

export function AttemptResult({ attempt }) {
  if (!attempt) return <span>No scored attempt</span>;
  return (
    <span>
      {attempt.correct_count}/{attempt.question_count} ·{" "}
      {attempt.percentage == null
        ? "Percentage unavailable"
        : `${attempt.percentage}%`}{" "}
      ·{" "}
      {attempt.passed == null
        ? "Pass state unavailable"
        : attempt.passed
          ? "Passed"
          : "Not passed"}{" "}
      · Attempt #{attempt.attempt_id}
      {attempt.score_basis === "current_bank_legacy_estimate"
        ? " · Historical total estimated from current quiz"
        : ""}
    </span>
  );
}
export default function AssessmentEvidence({
  assessments = [],
  reviewable = true,
}) {
  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">Assessment results</h3>
      {assessments.length ? (
        assessments.map((row) => (
          <article
            className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            key={row.quiz_id}
          >
            <h4 className="font-semibold">{row.title}</h4>
            <p className="mt-2 text-sm">
              Latest: <AttemptResult attempt={row.latest_attempt} />
            </p>
            <p className="mt-1 text-sm">
              Best: <AttemptResult attempt={row.best_attempt} />
            </p>
            <p className="mt-1 text-sm">
              {row.earned_pass
                ? "Passed: Yes"
                : "Passed: No"}
            </p>
            {row.legacy_passing_credit ? (
              <p className="text-sm">
                Prior passing credit retained; the original passing attempt is
                unavailable.
              </p>
            ) : null}
            {reviewable && row.latest_attempt ? (
              <Link
                className="mt-2 inline-block text-sm text-blue-600"
                to={`/quizzes/${row.quiz_id}/review`}
              >
                Review latest attempt
              </Link>
            ) : null}
          </article>
        ))
      ) : (
        <p className="text-sm text-slate-500">No course quizzes available.</p>
      )}
    </section>
  );
}
