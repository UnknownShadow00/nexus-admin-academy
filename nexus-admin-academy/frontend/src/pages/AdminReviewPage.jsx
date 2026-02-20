import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import { getReviewQueue, overrideSubmission, rejectProof, verifyProof } from "../services/api";

export default function AdminReviewPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [score, setScore] = useState(10);
  const [comment, setComment] = useState("");

  const load = async () => {
    setLoading(true);
    const res = await getReviewQueue();
    setItems(res.data || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3].map((id) => (
            <div key={id} className="panel animate-pulse dark:border-slate-700 dark:bg-slate-900">
              <div className="h-5 w-2/3 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="mt-3 h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-2 h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-4 h-9 w-full rounded bg-slate-200 dark:bg-slate-700" />
            </div>
          ))}
        </div>
      </main>
    );
  }

  if (!items.length) {
    return <main className="mx-auto max-w-6xl p-6"><EmptyState icon="📝" title="No submissions yet" message="Student work will appear here after they complete tickets" /></main>;
  }

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Manual Review Queue</h1>
      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <label className="text-sm">Override Score</label>
          <input className="input-field w-24" type="number" min={0} max={10} value={score} onChange={(e) => setScore(Number(e.target.value || 0))} />
          <input className="input-field min-w-64 flex-1" placeholder="Admin comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.submission_id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 p-3 dark:border-slate-700">
              <p className="text-sm text-slate-700 dark:text-slate-200">
                {item.student_name} - {item.ticket_title} - AI {item.ai_score}/10 - {item.status}
              </p>
              <div className="flex gap-2">
                <button className="btn-secondary" onClick={async () => { await overrideSubmission(item.submission_id, { new_score: score, comment: comment || "Manual review adjustment" }); await load(); }}>
                  Override
                </button>
                <button className="btn-primary" onClick={async () => { await verifyProof(item.submission_id, comment); await load(); }}>
                  Verify Proof
                </button>
                <button className="btn-secondary" onClick={async () => { await rejectProof(item.submission_id, comment); await load(); }}>
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
