import { Link } from "react-router-dom";
import { getCurrentStudent } from "../hooks/useAuth";

function percentage(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(100, Math.max(0, number)) : fallback;
}

function displayPercentage(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, "");
}

export function getAPlusPreviewAccess(student = getCurrentStudent()) {
  const progressPct = percentage(student?.a_plus_progress_pct, 0);
  const thresholdPct = percentage(student?.a_plus_unlock_threshold_pct, 40);

  return {
    locked: !student?.is_mentor && student?.a_plus_unlocked === false,
    progressPct,
    thresholdPct,
  };
}

export default function APlusPreviewLock({ access = getAPlusPreviewAccess(), className = "" }) {
  if (!access.locked) return null;

  return (
    <div
      className={`rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200 ${className}`}
      role="status"
    >
      <Link className="underline decoration-amber-500/60 underline-offset-2 hover:text-amber-700 dark:hover:text-amber-100" to="/study-tracker">
        Complete {displayPercentage(access.thresholdPct)}% of A+ Study Tracker to unlock hands-on work — you&apos;re at {displayPercentage(access.progressPct)}%.
      </Link>
    </div>
  );
}
