import { useEffect, useMemo, useState } from "react";
import Banner from "../../components/ui/Banner";
import { StatusBadge } from "../../components/ui/Badge";
import PageHeader from "../../components/ui/PageHeader";
import {
  getAdminServiceDeskAttempt,
  getAdminServiceDeskAttempts,
  submitServiceDeskMentorFeedback,
} from "../../services/api";

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function ModeBadge({ mode }) {
  return (
    <span className="inline-flex rounded-full bg-violet-100 px-2.5 py-1 text-xs font-medium text-violet-700 dark:bg-violet-950/30 dark:text-violet-300">
      {mode || "Unknown mode"}
    </span>
  );
}

function BooleanValue({ value }) {
  return <span className={value ? "text-emerald-600 dark:text-emerald-300" : "text-red-600 dark:text-red-300"}>{value ? "Yes" : "No"}</span>;
}

function JsonBlock({ value }) {
  let output;
  try {
    output = JSON.stringify(value, null, 2);
  } catch {
    output = String(value);
  }
  return (
    <details className="rounded-lg border border-slate-200 dark:border-slate-700">
      <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300">View raw JSON</summary>
      <pre className="max-h-64 overflow-auto border-t border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">{output}</pre>
    </details>
  );
}

function DetailField({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm text-slate-700 dark:text-slate-200">{children}</dd>
    </div>
  );
}

function ReviewSkeleton() {
  return (
    <div className="space-y-4">
      <div className="panel h-24 animate-pulse dark:border-slate-700 dark:bg-slate-900" />
      <div className="panel h-40 animate-pulse dark:border-slate-700 dark:bg-slate-900" />
      <div className="panel h-64 animate-pulse dark:border-slate-700 dark:bg-slate-900" />
    </div>
  );
}

export default function AdminServiceDeskReviewPage() {
  const [attempts, setAttempts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [studentFilter, setStudentFilter] = useState("");
  const [loadingAttempts, setLoadingAttempts] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [feedbackError, setFeedbackError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  const visibleAttempts = useMemo(() => {
    const query = studentFilter.trim().toLowerCase();
    if (!query) return attempts;
    return attempts.filter((attempt) =>
      [attempt.student_name, attempt.student_email].some((value) => String(value || "").toLowerCase().includes(query))
    );
  }, [attempts, studentFilter]);

  const selectedAttempt = attempts.find((attempt) => attempt.id === selectedId);

  async function loadAttempts() {
    setLoadingAttempts(true);
    setError("");
    try {
      const res = await getAdminServiceDeskAttempts({ limit: 200, offset: 0 }, { suppressToast: true });
      const rows = Array.isArray(res.data) ? res.data : [];
      setAttempts(rows);
      if (!selectedId && rows.length) setSelectedId(rows[0].id);
    } catch (err) {
      setAttempts([]);
      setError(err?.userMessage || "Unable to load Service Desk attempts.");
    } finally {
      setLoadingAttempts(false);
    }
  }

  useEffect(() => {
    loadAttempts();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return undefined;
    }
    let cancelled = false;
    const loadDetail = async () => {
      setLoadingDetail(true);
      setError("");
      setFeedbackError("");
      try {
        const res = await getAdminServiceDeskAttempt(selectedId, { suppressToast: true });
        if (!cancelled) {
          setDetail(res.data);
          setFeedback(res.data?.grade?.mentor_feedback || "");
        }
      } catch (err) {
        if (!cancelled) {
          setDetail(null);
          setError(err?.userMessage || "Unable to load Service Desk attempt detail.");
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function handleFeedbackSubmit(event) {
    event.preventDefault();
    if (!detail || !feedback.trim()) return;
    setActionLoading(true);
    setFeedbackError("");
    try {
      const res = await submitServiceDeskMentorFeedback(detail.id, feedback.trim(), { suppressToast: true });
      setDetail((current) => ({ ...current, grade: res.data }));
      setFeedback(res.data?.mentor_feedback || feedback.trim());
    } catch (err) {
      if (err?.response?.status === 404) {
        setFeedbackError("This attempt has no grade yet. Mentor feedback can be added after the student completes the scenario.");
      } else {
        setFeedbackError(err?.userMessage || "Unable to save mentor feedback.");
      }
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <PageHeader title="Service Desk Review" subtitle={`${attempts.length} attempt${attempts.length === 1 ? "" : "s"}`} />
      {error ? <Banner variant="error">{error} <button className="ml-2 underline" onClick={loadAttempts} type="button">Retry</button></Banner> : null}

      <div className="flex flex-col gap-4 lg:flex-row">
        <aside className="panel h-fit lg:w-1/3 dark:border-slate-700 dark:bg-slate-900">
          <label className="mb-3 block text-sm font-medium text-slate-700 dark:text-slate-200">
            Filter students
            <input className="input-field mt-1" value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)} placeholder="Name or email" />
          </label>
          {loadingAttempts ? (
            <div className="space-y-2">
              <div className="h-20 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
              <div className="h-20 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
            </div>
          ) : visibleAttempts.length ? (
            <div className="max-h-[42rem] space-y-2 overflow-auto pr-1">
              {visibleAttempts.map((attempt) => (
                <button
                  key={attempt.id}
                  className={`w-full rounded-lg border p-3 text-left transition-colors ${selectedId === attempt.id ? "border-blue-500 bg-blue-50 dark:border-blue-500 dark:bg-blue-950/30" : "border-slate-200 hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"}`}
                  onClick={() => setSelectedId(attempt.id)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-slate-100">{attempt.student_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{attempt.scenario_title}</p>
                    </div>
                    <p className="rounded-lg bg-slate-100 px-2 py-1 text-sm font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-200">{attempt.score ?? "-"}</p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2"><ModeBadge mode={attempt.mode} /><StatusBadge status={attempt.status} /></div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Started {formatDate(attempt.started_at)}</p>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">{attempts.length ? "No attempts match this student filter." : "No Service Desk attempts yet."}</p>
          )}
        </aside>

        <section className="panel min-h-96 flex-1 space-y-5 lg:w-2/3 dark:border-slate-700 dark:bg-slate-900">
          {!selectedId ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Select an attempt to review.</p>
          ) : loadingDetail ? (
            <ReviewSkeleton />
          ) : detail ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{selectedAttempt?.student_name} · {selectedAttempt?.student_email}</p>
                  <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{selectedAttempt?.scenario_title || "Service Desk scenario"}</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Scenario version ID {detail.scenario_version_id} · Attempt {detail.attempt_number ?? "-"}</p>
                </div>
                <div className="flex flex-wrap gap-2"><ModeBadge mode={detail.mode} /><StatusBadge status={detail.status} /></div>
              </div>

              <dl className="grid gap-4 rounded-lg border border-slate-200 p-4 sm:grid-cols-2 dark:border-slate-700">
                <DetailField label="Started">{formatDate(detail.started_at)}</DetailField>
                <DetailField label="Completed">{formatDate(detail.completed_at)}</DetailField>
                <DetailField label="Final score">{detail.score ?? detail.grade?.overall_score ?? "-"}</DetailField>
                <DetailField label="Passed"><BooleanValue value={detail.passed ?? detail.grade?.passed} /></DetailField>
              </dl>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Automated grading</h3>
                <div className="grid gap-3 rounded-lg border border-slate-200 p-4 sm:grid-cols-2 dark:border-slate-700">
                  <DetailField label="Rubric version">{detail.grade?.rubric_version || "Not graded"}</DetailField>
                  <DetailField label="Technical complete"><BooleanValue value={detail.grade?.technical_complete} /></DetailField>
                  <DetailField label="Critical failure"><BooleanValue value={detail.grade?.critical_failure} /></DetailField>
                  <DetailField label="Calculated">{formatDate(detail.grade?.calculated_at)}</DetailField>
                  <div className="sm:col-span-2"><DetailField label="Feedback summary">{detail.grade?.feedback_summary || "No automated feedback recorded."}</DetailField></div>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Current state</h3>
                <JsonBlock value={detail.current_state} />
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Event timeline</h3>
                <div className="space-y-2">
                  {detail.events?.length ? detail.events.map((event) => (
                    <div key={event.id || event.sequence_number} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-slate-800 dark:text-slate-100">#{event.sequence_number} {event.event_type}</span>{event.tool ? <ModeBadge mode={event.tool} /> : null}<StatusBadge status={event.success ? "completed" : "needs_revision"} /></div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">{formatDate(event.created_at)}</span>
                      </div>
                      <div className="mt-2"><JsonBlock value={event.payload} /></div>
                    </div>
                  )) : <p className="text-sm text-slate-500 dark:text-slate-400">No events recorded.</p>}
                </div>
              </div>

              <div className="space-y-3 border-t border-slate-200 pt-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Mentor feedback</h3>
                {detail.grade?.mentor_feedback ? <Banner><span className="font-semibold">Existing feedback ({detail.grade.mentor_feedback_by || "admin"}, {formatDate(detail.grade.mentor_feedback_at)}): </span>{detail.grade.mentor_feedback}</Banner> : null}
                {!detail.grade ? <Banner variant="warning">This attempt is still in progress. Mentor feedback can be added after a grade exists.</Banner> : <form className="space-y-3" onSubmit={handleFeedbackSubmit}><textarea className="input-field min-h-24" placeholder="Add mentor feedback..." value={feedback} onChange={(event) => setFeedback(event.target.value)} /><button className="btn-primary" disabled={actionLoading || !feedback.trim()} type="submit">{actionLoading ? "Saving..." : "Save feedback"}</button></form>}
                {feedbackError ? <Banner variant="error">{feedbackError}</Banner> : null}
              </div>
            </>
          ) : <p className="text-sm text-slate-500 dark:text-slate-400">Unable to load this attempt.</p>}
        </section>
      </div>
    </main>
  );
}
