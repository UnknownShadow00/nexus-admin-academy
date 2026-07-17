export const statusConfig = {
  completed: { label: "Completed", badgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300", iconName: "CheckCircle2" },
  in_progress: { label: "In Progress", badgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300", iconName: "Clock3" },
  not_started: { label: "Not Started", badgeClass: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300", iconName: "Circle" },
  pending: { label: "Pending", badgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300", iconName: "Hourglass" },
  passed: { label: "Passed", badgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300", iconName: "BadgeCheck" },
  needs_revision: { label: "Needs Revision", badgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300", iconName: "RotateCcw" },
  in_review: { label: "In Review", badgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300", iconName: "Search" },
  draft: { label: "Draft", badgeClass: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300", iconName: "FilePenLine" },
  published: { label: "Published", badgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300", iconName: "Send" },
  locked: { label: "Locked", badgeClass: "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300", iconName: "Lock" },
};

export const difficultyConfig = {
  1: { label: "Difficulty 1", badgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300", barClass: "bg-emerald-500" },
  2: { label: "Difficulty 2", badgeClass: "bg-lime-100 text-lime-700 dark:bg-lime-950/30 dark:text-lime-300", barClass: "bg-lime-500" },
  3: { label: "Difficulty 3", badgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300", barClass: "bg-amber-500" },
  4: { label: "Difficulty 4", badgeClass: "bg-orange-100 text-orange-700 dark:bg-orange-950/30 dark:text-orange-300", barClass: "bg-orange-500" },
  5: { label: "Difficulty 5", badgeClass: "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300", barClass: "bg-red-500" },
};

export const jobRelevanceConfig = {
  critical: { label: "Critical", badgeClass: "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300" },
  know: { label: "Need to Know", badgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" },
  awareness: { label: "Awareness", badgeClass: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
};

export function scoreBand(pct) {
  return pct >= 80 ? "good" : pct >= 60 ? "warn" : "poor";
}

scoreBand.classes = {
  good: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300",
  warn: "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300",
  poor: "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300",
};

export const iconSizes = { inline: 16, action: 20, heading: 24 };
