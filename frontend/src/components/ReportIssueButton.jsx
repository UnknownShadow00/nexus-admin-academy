import { Bug } from "lucide-react";
import { openIssueReport } from "../monitoring/sentry";

export default function ReportIssueButton({ onOpen = openIssueReport, compact = false }) {
  return (
    <button
      aria-label="Report Issue"
      className="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-300 px-3 py-2 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 dark:border-amber-700 dark:text-amber-200 dark:hover:bg-amber-950/30"
      onClick={onOpen}
      type="button"
    >
      <Bug aria-hidden="true" size={16} />
      <span className={compact ? "sr-only" : ""}>Report Issue</span>
    </button>
  );
}
