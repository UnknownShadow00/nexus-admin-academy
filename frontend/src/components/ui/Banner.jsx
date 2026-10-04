import { AlertCircle, AlertTriangle, CheckCircle2, Clock3, Info, MessageSquareText } from "lucide-react";

const variants = {
  info: {
    Icon: Info,
    className: "notice-info",
  },
  success: {
    Icon: CheckCircle2,
    className: "notice-success",
  },
  warning: {
    Icon: AlertTriangle,
    className: "notice-warning",
  },
  error: {
    Icon: AlertCircle,
    className: "notice-error",
  },
  mentor: {
    Icon: Clock3,
    className: "notice-mentor",
  },
  correction: {
    Icon: MessageSquareText,
    className: "notice-correction",
  },
};

export default function Banner({ variant = "info", children }) {
  const { Icon, className } = variants[variant] || variants.info;

  return (
    <div className={`notice ${className}`} role={variant === "error" ? "alert" : "status"}>
      <Icon className="mt-0.5 shrink-0" size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
