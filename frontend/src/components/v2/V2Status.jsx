import { Award, BadgeCheck, CheckCircle2, Circle, Clock3, Eye, Hourglass, Lock, MessageSquareText, RotateCcw } from "lucide-react";
import { getStatusPresentation, statusToneClasses } from "../ui/statusFoundation";

const icons = { Award, BadgeCheck, CheckCircle2, Circle, Clock3, Eye, Hourglass, Lock, MessageSquareText, RotateCcw };

export function statusLabel(status) {
  return getStatusPresentation(status === "completed" ? "done" : status === "failed" ? "not_quite" : status).label;
}

// Compatibility component for existing V2 pages during the redesign rollout.
export default function V2Status({ status = "not_started" }) {
  const { label, tone, iconName } = getStatusPresentation(status === "completed" ? "done" : status === "failed" ? "not_quite" : status);
  const Icon = icons[iconName] || Circle;
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${statusToneClasses[tone]}`}><Icon size={14} aria-hidden="true" />{label}</span>;
}
