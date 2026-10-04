// Presentation only. Keep server status values and progression rules unchanged.
export const statusFoundation = {
  not_started: { label: "Not started", tone: "neutral", iconName: "Circle" },
  locked: { label: "Locked", tone: "locked", iconName: "Lock" },
  in_progress: { label: "In progress", tone: "progress", iconName: "Clock3" },
  up_next: { label: "Up next", tone: "neutral", iconName: "Circle" },
  watched: { label: "Watched", tone: "neutral", iconName: "Eye" },
  viewed: { label: "Opened", tone: "neutral", iconName: "Eye" },
  completed: { label: "Completed", tone: "success", iconName: "CheckCircle2" },
  done: { label: "Done", tone: "success", iconName: "CheckCircle2" },
  passed: { label: "Passed", tone: "success", iconName: "BadgeCheck" },
  approved: { label: "Approved", tone: "success", iconName: "BadgeCheck" },
  not_quite: { label: "Not quite", tone: "correction", iconName: "RotateCcw" },
  mastered: { label: "Mastered", tone: "mastered", iconName: "Award" },
  awaiting_mentor_review: { label: "With your mentor", tone: "mentor", iconName: "Clock3" },
  needs_review: { label: "Waiting for grading", tone: "pending", iconName: "Hourglass" },
  pending: { label: "Pending", tone: "pending", iconName: "Hourglass" },
  check_required: { label: "Check required", tone: "pending", iconName: "Clock3" },
  needs_correction: { label: "Changes requested", tone: "correction", iconName: "MessageSquareText" },
  failed: { label: "Needs another try", tone: "error", iconName: "RotateCcw" },
  review_due: { label: "Review due", tone: "review", iconName: "Clock3" },
  optional: { label: "Optional", tone: "neutral", iconName: "Circle" },
};

export const statusToneClasses = {
  neutral: "status-tone status-tone-neutral",
  locked: "status-tone status-tone-locked",
  progress: "status-tone status-tone-progress",
  success: "status-tone status-tone-success",
  mastered: "status-tone status-tone-mastered",
  mentor: "status-tone status-tone-mentor",
  pending: "status-tone status-tone-pending",
  correction: "status-tone status-tone-correction",
  error: "status-tone status-tone-error",
  review: "status-tone status-tone-review",
};

export function getStatusPresentation(status) {
  return statusFoundation[status] || statusFoundation.not_started;
}

// A mentor's practical decision is a separate follow-up, not the whole stage's progress.
export function stageProgressStatus(progress) {
  if (progress?.module_complete) return "mastered";
  if (["awaiting_mentor_review", "needs_correction"].includes(progress?.status)) return "in_progress";
  return progress?.status || "not_started";
}

export function mentorFollowUpStatus(progress) {
  return ["awaiting_mentor_review", "needs_correction"].includes(progress?.status) ? progress.status : null;
}

export function practicalDisplayStatus(progress, beginner = false) {
  if (progress?.status === "needs_review") return "awaiting_mentor_review";
  if (progress?.detail?.review_decision === "reject" && (progress.status === "failed" || (beginner && progress.status === "in_progress"))) return "needs_correction";
  if (beginner && progress?.status === "passed") return "approved";
  return progress?.status || "not_started";
}
