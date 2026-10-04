import { Bug } from "lucide-react";
import { openIssueReport } from "../monitoring/sentry";

export default function ReportIssueButton({ onOpen = openIssueReport, compact = false }) {
  return (
    <button
      aria-label="Report Issue"
      className={compact ? "app-icon-button" : "btn-secondary"}
      onClick={onOpen}
      type="button"
    >
      <Bug aria-hidden="true" size={16} />
      <span className={compact ? "sr-only" : ""}>Report Issue</span>
    </button>
  );
}
