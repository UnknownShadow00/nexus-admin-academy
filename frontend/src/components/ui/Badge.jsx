import { Award, BadgeCheck, CheckCircle2, Circle, Clock3, FilePenLine, Hourglass, Lock, RotateCcw, Search, Send, Zap } from "lucide-react";
import { difficultyConfig, iconSizes, statusConfig } from "../../utils/theme";

const iconMap = { Award, BadgeCheck, CheckCircle2, Circle, Clock3, FilePenLine, Hourglass, Lock, RotateCcw, Search, Send, Zap };
const pill = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium";

export function StatusBadge({ status }) {
  const item = statusConfig[status] || statusConfig.not_started;
  const Icon = iconMap[item.iconName] || Circle;
  return <span className={`${pill} ${item.badgeClass}`}><Icon size={iconSizes.inline} aria-hidden="true" />{item.label}</span>;
}

export function DifficultyBadge({ level, showBar = false }) {
  const item = difficultyConfig[level] || difficultyConfig[1];
  return (
    <span className={`inline-flex flex-col overflow-hidden rounded-full ${item.badgeClass}`}>
      {showBar ? <span className={`h-1 w-full ${item.barClass}`} aria-hidden="true" /> : null}
      <span className={pill}><Award size={iconSizes.inline} aria-hidden="true" />{item.label}</span>
    </span>
  );
}

export function XPBadge({ amount }) {
  return <span className={`${pill} bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300`}><Zap size={iconSizes.inline} aria-hidden="true" />+{amount} XP</span>;
}

export const JOB_RELEVANCE_TAGS = {
  job_critical: { label: "Job Critical", cls: "bg-indigo-600 text-white border-indigo-600" },
  know_it: { label: "Know It", cls: "bg-slate-200 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700" },
  awareness: { label: "Awareness", cls: "bg-transparent text-slate-500 border-slate-300 dark:text-slate-300 dark:border-slate-600" },
};

export function JobRelevanceBadge({ value }) {
  const tag = JOB_RELEVANCE_TAGS[value];
  if (!tag) return null;
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${tag.cls}`}>{tag.label}</span>;
}
