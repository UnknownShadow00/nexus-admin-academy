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
