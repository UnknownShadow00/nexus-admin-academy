import { AlertCircle, AlertTriangle, Info } from "lucide-react";

const variants = {
  info: {
    Icon: Info,
    className:
      "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200",
  },
  warning: {
    Icon: AlertTriangle,
    className:
      "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200",
  },
  error: {
    Icon: AlertCircle,
    className:
      "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200",
  },
};

export default function Banner({ variant = "info", children }) {
  const { Icon, className } = variants[variant] || variants.info;

  return (
    <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium ${className}`}>
      <Icon size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
