import { CheckCircle2, Circle, Clock3, RotateCcw } from "lucide-react";

const labels = {
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
  passed: "Passed",
  mastered: "Mastered",
  watched: "Watched",
  check_required: "Check required",
  review_due: "Review due",
  optional: "Optional",
  locked: "Locked",
  failed: "Needs another try",
  needs_review: "Waiting for grading",
};

export function statusLabel(status) {
  return labels[status] || "Not started";
}

export default function V2Status({ status = "not_started" }) {
  const done = ["completed", "passed", "mastered"].includes(status);
  const waiting = ["needs_review", "watched", "check_required"].includes(status);
  const failed = status === "failed";
  const review = status === "review_due";
  const Icon = done ? CheckCircle2 : waiting ? Clock3 : failed ? RotateCcw : Circle;
  const classes = done
    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
    : review
      ? "bg-violet-50 text-violet-700 dark:bg-violet-950/30 dark:text-violet-300"
    : waiting
      ? "bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300"
      : failed
        ? "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300"
        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${classes}`}><Icon size={14} aria-hidden="true" />{statusLabel(status)}</span>;
}
