import { AlertCircle, BookOpenCheck, MessageSquareText, Users } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getV2MentorCohort, updateV2CohortFocus } from "../../services/api";

export const V2_MODULE_KEY = "module.aplus.core1.ip_configuration";

function label(value) {
  return String(value || "not_started").replaceAll("_", " ");
}

function Status({ value, score }) {
  const good = value === "passed" || value === "completed" || value === true;
  const bad = value === "failed" || value === "needs_review" || value === false;
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${good ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" : bad ? "bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{score != null ? `${score}% · ` : ""}{label(value)}</span>;
}

export default function V2MentorProgressPage() {
  const [moduleKey, setModuleKey] = useState(V2_MODULE_KEY);
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [focusBusy, setFocusBusy] = useState(false);
  const load = useCallback(() => {
    setError("");
    return getV2MentorCohort(moduleKey, { suppressToast: true })
      .then((res) => setData(res.data))
      .catch((err) => setError(err?.userMessage || "V2 mentor progress could not be loaded."));
  }, [moduleKey]);
  useEffect(() => { load(); }, [load]);

  const students = useMemo(() => (data?.students || []).filter((student) => {
    if (filter === "incomplete") return !student.completion.module_complete;
    if (filter === "failed_quiz") return student.module_quiz.passed === false;
    if (filter === "explain_review") return student.explain_status === "needs_review";
    if (filter.startsWith("weak:")) return student.weak_topics.some((row) => row.topic === filter.slice(5));
    return true;
  }), [data, filter]);

  async function saveFocus() {
    setFocusBusy(true);
    try { await updateV2CohortFocus(moduleKey, { suppressToast: true }); await load(); }
    catch (err) { setError(err?.userMessage || "Cohort Focus could not be updated."); }
    finally { setFocusBusy(false); }
  }

  if (error && !data) return <main className="mx-auto max-w-4xl p-6"><div className="panel" role="alert"><h1 className="text-xl font-bold">V2 mentor progress unavailable</h1><p className="mt-2 text-slate-600 dark:text-slate-300">{error}</p><button className="btn-primary mt-4" onClick={load}>Try again</button></div></main>;
  if (!data) return <main className="mx-auto max-w-7xl p-6" role="status">Loading V2 student progress...</main>;

  return <main className="mx-auto max-w-7xl space-y-6 p-4 pb-16 sm:p-6">
    <header><p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Mentor view</p><h1 className="mt-1 text-3xl font-bold">V2 Student Progress</h1><p className="mt-2 max-w-3xl text-slate-600 dark:text-slate-300">Actionable progress for the current development cohort. External practice remains self-reported and separate from Nexus results.</p><div className="mt-4 max-w-xl"><label className="block text-sm font-semibold" htmlFor="v2-mentor-module">Module</label><select id="v2-mentor-module" className="input-field mt-1 w-full" value={moduleKey} onChange={(event) => setModuleKey(event.target.value)}>{(data.available_modules || [{ module_key: data.module_key, title: data.students[0]?.module_title || "Current module" }]).map((module) => <option key={module.module_key} value={module.module_key}>{module.title}</option>)}</select></div></header>
    {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p> : null}

    <section className="panel" aria-labelledby="focus-heading"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 id="focus-heading" className="font-bold">Cohort Focus</h2><p className="mt-1 text-slate-600 dark:text-slate-300">{data.cohort_focus?.display || "No cohort focus set"}</p><p className="mt-1 text-xs text-slate-500">A teaching reference only; it does not gate student progress.</p></div><button className="btn-secondary" disabled={focusBusy || data.cohort_focus?.module_key === moduleKey} onClick={saveFocus}>{focusBusy ? "Saving..." : "Set to this module"}</button></div></section>

    <section aria-labelledby="students-heading"><div className="mb-3 flex flex-wrap items-end justify-between gap-3"><div><h2 id="students-heading" className="text-xl font-bold">Students</h2><p className="text-sm text-slate-500">{students.length} of {data.student_count} shown</p></div><label className="text-sm font-semibold">Filter<select className="input-field ml-2" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All students</option><option value="incomplete">Incomplete module</option><option value="failed_quiz">Failed Module Quiz</option><option value="explain_review">Explain needs review</option>{data.weak_areas.map((row) => <option key={row.topic} value={`weak:${row.topic}`}>Weak: {row.topic}</option>)}</select></label></div>
      {students.length ? <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"><table className="min-w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800"><tr><th className="p-3">Student / position</th><th className="p-3">Blocked by</th><th className="p-3">Lessons</th><th className="p-3">Module Quiz</th><th className="p-3">Practical</th><th className="p-3">Service Desk</th><th className="p-3">Explain</th><th className="p-3">Weak topics</th></tr></thead><tbody>{students.map((student) => <tr className="border-t border-slate-200 align-top dark:border-slate-700" key={student.student_id}><td className="p-3"><Link className="font-bold text-blue-600 hover:underline" to={`/admin/v2-progress/students/${student.student_id}?module=${encodeURIComponent(moduleKey)}`}>{student.student_name}</Link><p className="mt-1 text-xs text-slate-500">Current: {student.current_position.title}</p></td><td className="p-3">{student.completion.module_complete ? "Not blocked" : student.blockers?.[0]?.label || "Next activity not completed"}</td><td className="p-3 font-semibold">{student.completion.lessons_completed} / {student.completion.lessons_total}</td><td className="p-3"><Status value={student.module_quiz.status} score={student.module_quiz.score} /></td><td className="p-3"><Status value={student.practical?.status} score={student.practical?.score} /></td><td className="p-3"><Status value={student.service_desk?.status} score={student.service_desk?.score} /></td><td className="p-3"><Status value={student.explain_status} /></td><td className="p-3">{student.weak_topics.length ? student.weak_topics.map((row) => <span className="mb-1 mr-1 inline-flex rounded-full bg-rose-50 px-2 py-1 text-xs text-rose-700 dark:bg-rose-950/30 dark:text-rose-300" key={row.topic}>{row.topic} · {row.missed_count}</span>) : <span className="text-slate-500">None identified</span>}</td></tr>)}</tbody></table></div> : <div className="panel text-center text-slate-500">No students match this filter.</div>}
    </section>

    <div className="grid gap-6 lg:grid-cols-2">
      <section className="panel" aria-labelledby="review-heading"><div className="flex items-center gap-2"><AlertCircle className="text-amber-600" size={20} /><h2 id="review-heading" className="text-xl font-bold">Needs Review</h2></div>{data.needs_review.length ? <ul className="mt-4 space-y-3">{data.needs_review.map((job) => <li className="rounded-xl border border-slate-200 p-3 dark:border-slate-700" key={job.pending_grade_id}><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">Student #{job.student_id} · {label(job.source_type)}</p><p className="mt-1 text-sm text-slate-500">{label(job.status)} · priority {job.priority}</p></div><Link className="btn-secondary" to={`/admin/v2-grading/${job.pending_grade_id}`}>Review</Link></div></li>)}</ul> : <p className="mt-4 text-sm text-slate-500">No Explain responses need review.</p>}</section>
      <section className="panel" aria-labelledby="weak-heading"><div className="flex items-center gap-2"><Users className="text-blue-600" size={20} /><h2 id="weak-heading" className="text-xl font-bold">Cohort Weak Areas</h2></div>{data.weak_areas.length ? <ul className="mt-4 space-y-3">{data.weak_areas.map((row) => <li key={row.topic}><strong>{row.topic}</strong><p className="text-sm text-slate-500">{row.students_affected} of {row.student_count} students · {row.total_misses} assessment misses{row.students_with_repeated_misses ? ` · ${row.students_with_repeated_misses} with repeated misses` : ""}</p></li>)}</ul> : <p className="mt-4 text-sm text-slate-500">No cohort weaknesses identified yet.</p>}</section>
      <section className="panel" aria-labelledby="topics-heading"><div className="flex items-center gap-2"><BookOpenCheck className="text-violet-600" size={20} /><h2 id="topics-heading" className="text-xl font-bold">Suggested Review Topics</h2></div>{data.suggested_review_topics.length ? <ol className="mt-4 list-decimal space-y-2 pl-5">{data.suggested_review_topics.map((row) => <li key={row.topic}><strong>{row.topic}</strong> — {row.reason}</li>)}</ol> : <p className="mt-4 text-sm text-slate-500">Suggestions appear after Nexus assessment misses are recorded.</p>}</section>
      <section className="panel" aria-labelledby="questions-heading"><div className="flex items-center gap-2"><MessageSquareText className="text-emerald-600" size={20} /><h2 id="questions-heading" className="text-xl font-bold">Student Questions & Notes</h2></div>{data.student_questions.length ? <ul className="mt-4 space-y-3">{data.student_questions.map((note, index) => <li className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800" key={`${note.student_id}-${note.resource_key}-${index}`}><strong>{note.student_name}</strong><p className="mt-1 text-xs font-semibold uppercase text-slate-500">Self-reported external practice · {note.resource}</p>{note.student_note ? <p className="mt-2">Note: “{note.student_note}”</p> : null}{note.confusing_topic ? <p className="mt-1">Confusing topic: {note.confusing_topic}</p> : null}{note.question_for_mentor ? <p className="mt-1 font-semibold">Question: {note.question_for_mentor}</p> : null}</li>)}</ul> : <p className="mt-4 text-sm text-slate-500">No student questions or notes have been reported.</p>}</section>
    </div>
  </main>;
}
