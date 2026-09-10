import { Brain } from "lucide-react";
import { useState } from "react";

import FlashcardReviewPanel from "./FlashcardReviewPanel";

export default function TodayReviewCard({ summary, error, onRetry }) {
  const [started, setStarted] = useState(false);

  if (error) {
    return (
      <section className="rounded-xl border border-rose-200 bg-rose-50 p-4" role="alert">
        <h2 className="font-semibold text-rose-900">We couldn’t load your review items.</h2>
        <button className="btn-secondary mt-3" onClick={onRetry} type="button">Try again</button>
      </section>
    );
  }
  if (!summary || summary.review_state !== "due") return null;
  if (started) {
    return <section className="panel"><FlashcardReviewPanel /></section>;
  }
  const priorityCount = summary.priority_count ?? summary.due_count;
  const minutes = Math.max(3, Math.min(10, priorityCount * 2));
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3"><Brain className="mt-0.5 text-amber-700" size={20} /><div><h2 className="font-semibold">Review {priorityCount} concept{priorityCount === 1 ? "" : "s"}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">About {minutes} minutes · reinforces recent misses</p></div></div>
      <button className="btn-secondary shrink-0" onClick={() => setStarted(true)} type="button">Start review</button>
    </section>
  );
}
