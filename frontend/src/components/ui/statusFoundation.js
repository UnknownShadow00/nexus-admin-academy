// Presentation only. Keep server status values and progression rules unchanged.
export const statusFoundation = {
  not_started: { label: "Not started", tone: "neutral", iconName: "Circle" },
  locked: { label: "Locked", tone: "locked", iconName: "Lock" },
  in_progress: { label: "In progress", tone: "progress", iconName: "Clock3" },
  watched: { label: "Watched", tone: "viewed", iconName: "Eye" },
  viewed: { label: "Viewed / Opened", tone: "viewed", iconName: "Eye" },
  completed: { label: "Completed", tone: "success", iconName: "CheckCircle2" },
  passed: { label: "Passed", tone: "success", iconName: "BadgeCheck" },
  mastered: { label: "Mastered", tone: "mastered", iconName: "Award" },
  awaiting_mentor_review: { label: "Awaiting mentor review", tone: "pending", iconName: "Hourglass" },
  needs_review: { label: "Waiting for grading", tone: "pending", iconName: "Hourglass" },
  pending: { label: "Pending", tone: "pending", iconName: "Hourglass" },
  check_required: { label: "Check required", tone: "pending", iconName: "Clock3" },
  needs_correction: { label: "Needs correction", tone: "correction", iconName: "RotateCcw" },
  failed: { label: "Needs another try", tone: "error", iconName: "RotateCcw" },
  review_due: { label: "Review due", tone: "review", iconName: "Clock3" },
  optional: { label: "Optional", tone: "neutral", iconName: "Circle" },
};

export const statusToneClasses = {
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  locked: "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100",
  progress: "bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-200",
  viewed: "bg-cyan-100 text-cyan-900 dark:bg-cyan-950 dark:text-cyan-200",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200",
  mastered: "bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-200",
  pending: "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200",
  correction: "bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-200",
  error: "bg-red-100 text-red-900 dark:bg-red-950/50 dark:text-red-200",
  review: "bg-violet-100 text-violet-900 dark:bg-violet-950/50 dark:text-violet-200",
};

export function getStatusPresentation(status) {
  return statusFoundation[status] || statusFoundation.not_started;
}
