import { Lock } from "lucide-react";
import { Link } from "react-router-dom";

export default function V2LockedActivity({ activity, moduleRoute }) {
  const unavailable = activity.unavailable || {};
  return <article className="panel flex min-h-48 flex-col" aria-label={`${activity.title} unavailable`}>
    <div className="flex items-start justify-between gap-3">
      <span className="rounded-xl bg-slate-100 p-2.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300"><Lock size={20} aria-hidden="true" /></span>
      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">Not available yet</span>
    </div>
    <h3 className="mt-4 font-bold">{activity.title}</h3>
    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300"><strong>Why:</strong> {unavailable.reason || "This activity is not available yet."}</p>
    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300"><strong>Next:</strong> {unavailable.required_action || "Choose another available activity in this module."}</p>
    <Link className="mt-auto pt-4 text-sm font-semibold text-blue-600 dark:text-blue-400" to={unavailable.blocker_route || moduleRoute}>Back to module →</Link>
  </article>;
}
