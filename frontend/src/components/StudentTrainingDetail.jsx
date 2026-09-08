import AssessmentEvidence from "./AssessmentEvidence";
import { useEffect, useState } from "react";
import { getStudentTrainingProgress } from "../services/api";

export default function StudentTrainingDetail({
  studentId,
  cachedProgress,
  onProgressLoaded,
}) {
  const [loading, setLoading] = useState(!cachedProgress);
  const [error, setError] = useState("");

  useEffect(() => {
    if (cachedProgress) {
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    getStudentTrainingProgress(studentId, { suppressToast: true })
      .then((response) => {
        if (!cancelled) onProgressLoaded(studentId, response.data);
      })
      .catch(() => {
        if (!cancelled) setError("Training progress could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [cachedProgress, onProgressLoaded, studentId]);

  if (loading) {
    return <div className="h-24 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />;
  }
  if (error) {
    return <p className="text-sm text-red-600 dark:text-red-400">{error}</p>;
  }
  if (!cachedProgress) return null;

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100">Weekly Roadmap</h3>
        <ul className="mt-2 space-y-2">
          {(cachedProgress.weekly_roadmap || []).map((week) => (
            <li key={week.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">Week {week.week_number} · {week.title}</span>
                <span>{week.completion_percent}%</span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                role="progressbar"
                aria-label={`Week ${week.week_number} completion`}
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow={week.completion_percent}
              >
                <div
                  className="h-full rounded-full bg-blue-600"
                  style={{ width: `${week.completion_percent}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {week.required_complete} of {week.required_total} required · {week.status.replaceAll("_", " ")}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">Required quizzes passed: {cachedProgress.required_quizzes?.completed ?? 0} / {cachedProgress.required_quizzes?.total ?? 0}</h3>
        <AssessmentEvidence reviewable={false} assessments={cachedProgress.assessments} />
      </section>
    </div>
  );
}
