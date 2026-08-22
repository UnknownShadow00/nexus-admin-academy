import { CheckCircle2, Circle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getOrientationProgress, getWeekPlan } from "../services/api";

function Step({ complete, children }) {
  const Icon = complete ? CheckCircle2 : Circle;
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
      <span className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <Icon
          aria-hidden="true"
          className={complete ? "shrink-0 text-emerald-600" : "shrink-0 text-slate-400"}
          size={20}
        />
        {children}
      </span>
    </li>
  );
}

export default function OrientationPracticePanel({ completing, onMarkComplete, refreshKey = 0 }) {
  const [progress, setProgress] = useState(null);
  const [nextAction, setNextAction] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setProgress(null);
    getOrientationProgress({ suppressToast: true })
      .then((response) => {
        if (!cancelled) setProgress(response.data || null);
      })
      .catch(() => {
        if (!cancelled) setProgress(null);
      });
    return () => { cancelled = true; };
  }, [refreshKey]);

  useEffect(() => {
    if (!progress?.is_complete || !progress?.week_one_unlocked) {
      setNextAction(null);
      return;
    }
    let cancelled = false;
    getWeekPlan(1, { suppressToast: true })
      .then((response) => {
        if (!cancelled) setNextAction(response.data?.next_action || null);
      })
      .catch(() => {
        if (!cancelled) setNextAction(null);
      });
    return () => { cancelled = true; };
  }, [progress?.is_complete, progress?.week_one_unlocked]);

  if (!progress) {
    return <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">Loading your orientation checklist…</div>;
  }

  const steps = progress.steps || {};
  const remainingMessage = !steps.lesson_completion && !steps.quiz
    ? "Complete the orientation and pass the Ticketing Systems Quiz to unlock Support Workflow Essentials."
    : !steps.lesson_completion
      ? "Mark the orientation complete to unlock Support Workflow Essentials."
      : "Pass the Ticketing Systems Quiz to unlock Support Workflow Essentials.";

  return (
    <section className="panel space-y-4" aria-labelledby="week-zero-checklist">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">Orientation Module</p>
        <h2 className="mt-1 text-xl font-bold" id="week-zero-checklist">Two quick steps</h2>
      </div>

      <ol className="space-y-2">
        <Step complete={steps.lesson_completion}>
          <span className="font-semibold">Read orientation</span>
          <button
            className="btn-primary ml-7 shrink-0 text-sm sm:ml-auto"
            disabled={steps.lesson_completion || completing}
            onClick={onMarkComplete}
            type="button"
          >
            {steps.lesson_completion ? "Orientation complete" : completing ? "Saving…" : "Mark lesson complete"}
          </button>
        </Step>
        <Step complete={steps.quiz}>
          <span className="font-semibold">Take Ticketing Systems Quiz</span>
          <Link className="ml-7 shrink-0 font-semibold text-blue-700 underline dark:text-blue-300 sm:ml-auto" to={progress.quiz_route}>
            {steps.quiz ? "Review quiz" : "Take quiz"}
          </Link>
        </Step>
      </ol>

      {progress.is_complete && progress.week_one_unlocked ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100">
          <p className="font-bold">✓ Orientation complete</p>
          {nextAction ? (
            <Link className="btn-primary mt-3 text-sm" to={nextAction.route}>Start Next Module</Link>
          ) : (
            <Link className="btn-primary mt-3 text-sm" to="/training/module/module.endpoint.support_workflow">Start Next Module</Link>
          )}
        </div>
      ) : (
        <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/70 dark:text-slate-300">
          {remainingMessage}
        </p>
      )}
    </section>
  );
}
