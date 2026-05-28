import { useEffect, useMemo, useState } from "react";
import Banner from "../../components/ui/Banner";
import { StatusBadge } from "../../components/ui/Badge";
import PageHeader from "../../components/ui/PageHeader";
import {
  getAdminReviewQueue,
  getAdminSubmission,
  overrideScore,
  rejectSubmission,
  verifySubmission,
} from "../../services/api";

function formatDate(value) {
  if (!value) return "Not submitted";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function ReviewedBadge({ reviewed }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
        reviewed
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
      }`}
    >
      {reviewed ? "Reviewed" : "Unreviewed"}
    </span>
  );
}

function FeedbackBlock({ feedback }) {
  const parsed = useMemo(() => {
    if (!feedback) return null;
    if (typeof feedback === "object") return feedback;
    try {
      return JSON.parse(feedback);
    } catch {
      return null;
    }
  }, [feedback]);

  if (!feedback) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No AI feedback recorded.</p>;
  }

  if (!parsed || typeof parsed !== "object") {
    return <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{String(feedback)}</p>;
  }

  return (
    <div className="space-y-2">
      {Object.entries(parsed).map(([key, value]) => (
        <div key={key} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{key.replaceAll("_", " ")}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
            {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function AdminTicketReviewPage() {
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [comment, setComment] = useState("");
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideValue, setOverrideValue] = useState(10);
  const [overrideComment, setOverrideComment] = useState("");
  const [error, setError] = useState("");

  const selectedQueueItem = queue.find((item) => item.submission_id === selectedId);

  async function loadQueue() {
    setLoadingQueue(true);
    setError("");
    try {
      const res = await getAdminReviewQueue({ suppressToast: true });
      const rows = Array.isArray(res.data) ? res.data : [];
      setQueue(rows);
      if (!selectedId && rows.length) setSelectedId(rows[0].submission_id);
    } catch (err) {
      setQueue([]);
      setError(err?.userMessage || "Unable to load review queue.");
    } finally {
      setLoadingQueue(false);
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    const run = async () => {
      setLoadingDetail(true);
      setError("");
      try {
        const res = await getAdminSubmission(selectedId, { suppressToast: true });
        if (!cancelled) {
          setDetail(res.data);
          setComment("");
          setOverrideValue(Number(res.data?.ai_score ?? 10));
          setOverrideComment(res.data?.admin_comment || "");
          setOverrideOpen(false);
        }
      } catch (err) {
        if (!cancelled) {
          setDetail(null);
          setError(err?.userMessage || "Unable to load submission detail.");
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function refreshSelected() {
    await loadQueue();
    if (selectedId) {
      const res = await getAdminSubmission(selectedId, { suppressToast: true });
      setDetail(res.data);
    }
  }

  async function runAction(name, action) {
    setActionLoading(name);
    setError("");
    try {
      await action();
      await refreshSelected();
    } catch (err) {
      setError(err?.userMessage || "Action failed.");
    } finally {
      setActionLoading("");
    }
  }

  const submittedAt = selectedQueueItem?.submitted_at || detail?.submitted_at;

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <PageHeader title="Ticket Review Queue" subtitle={`${queue.length} graded submission${queue.length === 1 ? "" : "s"}`} />
      {error ? <Banner variant="error">{error}</Banner> : null}

      <div className="flex flex-col gap-4 lg:flex-row">
        <aside className="panel h-fit lg:w-1/3 dark:border-slate-700 dark:bg-slate-900">
          {loadingQueue ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Loading submissions...</p>
          ) : queue.length ? (
            <div className="max-h-[42rem] space-y-2 overflow-auto pr-1">
              {queue.map((item) => (
                <button
                  key={item.submission_id}
                  className={`w-full rounded-lg border p-3 text-left transition-colors ${
                    selectedId === item.submission_id
                      ? "border-blue-500 bg-blue-50 dark:border-blue-500 dark:bg-blue-950/30"
                      : "border-slate-200 hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  }`}
                  onClick={() => setSelectedId(item.submission_id)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-slate-100">{item.student_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{item.ticket_title}</p>
                    </div>
                    <p className="rounded-lg bg-slate-100 px-2 py-1 text-sm font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                      {item.ai_score ?? "-"}/10
                    </p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <StatusBadge status={item.status} />
                    <ReviewedBadge reviewed={item.admin_reviewed} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">No graded submissions are ready for review.</p>
          )}
        </aside>

        <section className="panel min-h-96 flex-1 space-y-5 lg:w-2/3 dark:border-slate-700 dark:bg-slate-900">
          {!selectedId ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Select a submission to review.</p>
          ) : loadingDetail ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Loading submission detail...</p>
          ) : detail ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{detail.student_name || selectedQueueItem?.student_name}</p>
                  <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                    {detail.ticket_title || selectedQueueItem?.ticket_title}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Submitted {formatDate(submittedAt)}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={detail.status} />
                  <ReviewedBadge reviewed={detail.admin_reviewed} />
                </div>
              </div>

              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950/30">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">AI Score</p>
                <p className="text-4xl font-bold text-blue-800 dark:text-blue-200">{detail.ai_score ?? "-"}/10</p>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Ticket Writeup</h3>
                <div className="max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
                  <p className="whitespace-pre-wrap">{detail.writeup || "No writeup submitted."}</p>
                </div>
              </div>

              {detail.commands_used ? (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Commands Used</h3>
                  <pre className="overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700 dark:bg-slate-950 dark:text-slate-200">
                    <code>{detail.commands_used}</code>
                  </pre>
                </div>
              ) : null}

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">AI Feedback</h3>
                <FeedbackBlock feedback={detail.ai_feedback} />
              </div>

              {detail.admin_reviewed && detail.admin_comment ? (
                <Banner>
                  <span className="font-semibold">Admin comment: </span>
                  {detail.admin_comment}
                </Banner>
              ) : null}

              <div className="space-y-3 border-t border-slate-200 pt-4 dark:border-slate-700">
                <textarea
                  className="input-field min-h-24"
                  placeholder="Optional admin comment..."
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
                <div className="flex flex-wrap gap-2">
                  <button
                    className="btn-primary"
                    disabled={actionLoading !== "" || detail.xp_granted}
                    onClick={() => runAction("verify", () => verifySubmission(detail.id, comment))}
                    type="button"
                  >
                    {actionLoading === "verify" ? "Granting..." : detail.xp_granted ? "XP Granted" : "Pass + Grant XP"}
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={actionLoading !== "" || detail.xp_granted}
                    onClick={() => runAction("reject", () => rejectSubmission(detail.id, comment))}
                    type="button"
                  >
                    {actionLoading === "reject" ? "Rejecting..." : "Needs Revision"}
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={actionLoading !== ""}
                    onClick={() => setOverrideOpen((open) => !open)}
                    type="button"
                  >
                    Override Score
                  </button>
                </div>

                {overrideOpen ? (
                  <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    <div className="grid gap-3 md:grid-cols-[8rem_1fr_auto] md:items-end">
                      <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        Score
                        <input
                          className="input-field mt-1"
                          max={10}
                          min={0}
                          type="number"
                          value={overrideValue}
                          onChange={(event) => setOverrideValue(Number(event.target.value || 0))}
                        />
                      </label>
                      <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        Comment
                        <input
                          className="input-field mt-1"
                          value={overrideComment}
                          onChange={(event) => setOverrideComment(event.target.value)}
                          placeholder="Reason for score change"
                        />
                      </label>
                      <button
                        className="btn-primary"
                        disabled={actionLoading !== ""}
                        onClick={() => runAction("override", () => overrideScore(detail.id, overrideValue, overrideComment))}
                        type="button"
                      >
                        {actionLoading === "override" ? "Saving..." : "Save Override"}
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">Unable to load this submission.</p>
          )}
        </section>
      </div>
    </main>
  );
}
