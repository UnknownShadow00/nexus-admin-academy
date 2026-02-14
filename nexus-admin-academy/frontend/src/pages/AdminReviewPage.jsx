import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import { getReviewQueue, overrideSubmission } from "../services/api";

export default function AdminReviewPage() {
  const [items, setItems] = useState([]);
  const [score, setScore] = useState(10);

  const load = async () => {
    const res = await getReviewQueue();
    setItems(res.data || []);
  };

  useEffect(() => { load(); }, []);

  if (!items.length) {
    return <main className="mx-auto max-w-6xl p-6"><EmptyState icon="??" title="No submissions yet" message="Student work will appear here after they complete tickets" /></main>;
  }

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Manual Review Queue</h1>
      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <div className="mb-3 flex items-center gap-2">
          <label className="text-sm">Override Score</label>
          <input className="input-field w-24" type="number" min={0} max={10} value={score} onChange={(e) => setScore(Number(e.target.value || 0))} />
        </div>
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.submission_id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 p-3 dark:border-slate-700">
              <p className="text-sm text-slate-700 dark:text-slate-200">{item.student_name} ? {item.ticket_title} ? AI {item.ai_score}/10</p>
              <button className="btn-secondary" onClick={async () => { await overrideSubmission(item.submission_id, { new_score: score, comment: "Manual review adjustment" }); await load(); }}>
                Mark Reviewed
              </button>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
