import toast from "react-hot-toast";
import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import { getReviewQueue, overrideSubmission, rejectProof, verifyProof } from "../services/api";

export default function AdminReviewPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rowState, setRowState] = useState({});

  const load = async () => {
    setLoading(true);
    const res = await getReviewQueue();
    setItems(res.data || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const getRow = (id) => rowState[id] || { score: 10, comment: "" };
  const setRow = (id, patch) => setRowState((s) => ({ ...s, [id]: { ...getRow(id), ...patch } }));

  const doOverride = async (item) => {
    const { score, comment } = getRow(item.submission_id);
    try {
      await overrideSubmission(item.submission_id, { new_score: score, comment: comment || "Manual review adjustment" });
      toast.success("Score overridden");
      setRow(item.submission_id, { score: 10, comment: "" });
      await load();
    } catch {
      toast.error("Override failed");
    }
  };

  const doVerify = async (item) => {
    const { comment } = getRow(item.submission_id);
    try {
      await verifyProof(item.submission_id, comment);
      toast.success("Proof verified");
      setRow(item.submission_id, { score: 10, comment: "" });
      await load();
    } catch {
      toast.error("Verify failed");
    }
  };

  const doReject = async (item) => {
    const { comment } = getRow(item.submission_id);
    try {
      await rejectProof(item.submission_id, comment);
      toast.success("Submission rejected");
      setRow(item.submission_id, { score: 10, comment: "" });
      await load();
    } catch {
      toast.error("Reject failed");
    }
  };

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
    return <main className="mx-auto max-w-6xl p-6"><EmptyState icon="*" title="No submissions yet" message="Student work will appear here after they complete tickets" /></main>;
  }

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Manual Review Queue</h1>
      <div className="space-y-3">
        {items.map((item) => {
          const { score, comment } = getRow(item.submission_id);
          return (
            <div key={item.submission_id} className="panel dark:bg-slate-900 dark:border-slate-700">
              <p className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-200">
                {item.student_name} - {item.ticket_title} - AI {item.ai_score}/10 - {item.status}
              </p>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <label className="text-sm text-slate-600 dark:text-slate-400">Override score</label>
                <input className="input-field w-24" type="number" min={0} max={10} value={score} onChange={(e) => setRow(item.submission_id, { score: Number(e.target.value || 0) })} />
                <input className="input-field min-w-48 flex-1" placeholder="Admin comment (optional)" value={comment} onChange={(e) => setRow(item.submission_id, { comment: e.target.value })} />
              </div>
              <div className="flex gap-2">
                <button className="btn-secondary" onClick={() => doOverride(item)}>Override</button>
                <button className="btn-primary" onClick={() => doVerify(item)}>Verify Proof</button>
                <button className="btn-secondary" onClick={() => doReject(item)}>Reject</button>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
