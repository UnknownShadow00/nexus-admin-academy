import { AlertCircle, BookOpen, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function ReviewEvidence({ summary, error, onRetry }) {
  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900 dark:border-rose-900 dark:bg-rose-950/20 dark:text-rose-200" role="alert">
        <div className="flex items-center gap-2 font-semibold"><AlertCircle size={18} />We couldn’t load your review items.</div>
        <button className="btn-secondary mt-3" onClick={onRetry} type="button">Try again</button>
      </div>
    );
  }

  if (!summary) return <p className="text-sm text-slate-500">Loading review priorities…</p>;
  if (summary.review_state === "fresh") {
    return (
      <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
        <p className="font-semibold">Review will appear after you complete some learning.</p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Your first lesson and assessment will give Nexus something useful to reinforce.</p>
      </div>
    );
  }
  if (summary.review_state === "clear") {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-200">
        <CheckCircle2 size={18} /><p className="font-semibold">No review is due right now.</p>
      </div>
    );
  }

  const priorityCount = summary.priority_count ?? (summary.priorities || []).length;

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">Review {priorityCount} concept{priorityCount === 1 ? "" : "s"} · about {Math.max(3, Math.min(10, priorityCount * 2))} minutes</p>
      {(summary.priorities || []).map((item) => (
        <article className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20" key={item.question_id}>
          <div className="flex items-start gap-3"><BookOpen className="mt-0.5 shrink-0 text-amber-700" size={18} /><div><h3 className="font-semibold text-slate-950 dark:text-white">{item.concept_name}</h3><p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{item.reason}</p></div></div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link className="btn-primary" to={item.review_url}>Review worked example</Link>
            {item.practice_url ? <Link className="btn-secondary" to={item.practice_url}>{item.practice_label || "Practice related questions"}</Link> : null}
          </div>
        </article>
      ))}
      {summary.due_count > priorityCount ? <p className="text-xs text-slate-500">Showing the most useful priorities first.</p> : null}
    </div>
  );
}
