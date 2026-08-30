import { ArrowLeft, ArrowRight, Check, ExternalLink } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2Status from "../../components/v2/V2Status";
import { completeV2Lesson, getV2Lesson, recordV2Resource } from "../../services/api";

function ResourceCard({ resource, moduleKey, onChanged }) {
  const [busy, setBusy] = useState(false);
  async function openResource() {
    setBusy(true);
    try {
      await recordV2Resource(moduleKey, resource.key, { opened: true }, { suppressToast: true });
      onChanged();
    } finally { setBusy(false); }
  }
  async function completeResource() {
    setBusy(true);
    try { await recordV2Resource(moduleKey, resource.key, { completed: true }, { suppressToast: true }); onChanged(); } finally { setBusy(false); }
  }
  return <article className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${resource.required ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{resource.required ? "Required" : "Optional"}</span><h3 className="mt-3 font-bold">{resource.title}</h3><p className="mt-1 text-sm text-slate-500">{resource.provider || "Learning resource"} · {resource.type?.replaceAll("_", " ")}{resource.duration ? ` · ${resource.duration}` : ""}</p></div>{resource.completed ? <V2Status status="completed" /> : null}</div>
    <div className="mt-4 flex flex-wrap gap-2">
      {resource.url ? <a className="btn-secondary inline-flex items-center gap-2" href={resource.url} onClick={openResource} target="_blank" rel="noopener noreferrer">Open resource <ExternalLink size={15} aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span></a> : <span className="text-sm text-slate-500">Resource link unavailable</span>}
      <button className="btn-secondary inline-flex items-center gap-2" disabled={busy || resource.completed} onClick={completeResource} type="button">{resource.completed ? "Completed" : "Mark completed"}{resource.completed ? <Check size={15} aria-hidden="true" /> : null}</button>
    </div>
    {resource.opened_at && !resource.completed ? <p className="mt-3 text-xs text-slate-500">Opened. Mark it complete when you finish.</p> : null}
  </article>;
}

const markdownComponents = {
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>,
  table: ({ children }) => <div className="overflow-x-auto"><table>{children}</table></div>,
};

export default function V2LessonPage() {
  const { moduleKey, lessonKey } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { setError(""); getV2Lesson(moduleKey, lessonKey, { suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.response?.status === 404 ? "That lesson could not be found." : err?.userMessage || "The lesson could not be loaded.")); }, [lessonKey, moduleKey]);
  useEffect(load, [load]);
  async function markComplete() { setBusy(true); try { await completeV2Lesson(moduleKey, lessonKey); await load(); } finally { setBusy(false); } }
  if (error) return <V2Error title="Lesson unavailable" message={error} onRetry={load} />;
  if (!data) return <V2Loading text="Loading lesson..." />;
  const lesson = data.lesson;
  const completed = ["completed", "passed"].includes(lesson.progress.status);
  const lessonRoute = (key) => `/learning-v2/modules/${moduleKey}/lessons/${key}`;
  return <main className="mx-auto max-w-5xl space-y-6 p-4 pb-24 sm:p-6">
    <V2Breadcrumbs certification={data.certification} module={data.module} lesson={lesson} />
    <header className="max-w-3xl"><div className="flex flex-wrap items-center gap-2"><V2Status status={lesson.progress.status} />{lesson.importance === "job_critical" ? <span className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-950/30 dark:text-violet-300">Useful on the job</span> : null}</div><h1 className="mt-4 text-3xl font-bold text-slate-950 dark:text-white sm:text-4xl">{lesson.title}</h1>{lesson.summary ? <p className="mt-3 text-lg text-slate-600 dark:text-slate-300">{lesson.summary}</p> : null}<p className="mt-2 text-sm text-slate-500">About {lesson.estimated_minutes || "a few"} minutes</p></header>
    <article className="panel v2-markdown max-w-none"><ReactMarkdown components={markdownComponents}>{lesson.content_markdown}</ReactMarkdown></article>
    <section aria-labelledby="resources-title" className="panel space-y-4"><div><p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Watch / read</p><h2 id="resources-title" className="mt-1 text-2xl font-bold">Lesson resources</h2><p className="mt-1 text-sm text-slate-500">Opening a link does not complete it. Mark it complete after you finish.</p></div>{lesson.resources.length ? lesson.resources.map((resource) => <ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800">No resources are mapped to this lesson.</p>}</section>
    {lesson.quick_check ? <section className="rounded-2xl border border-violet-200 bg-violet-50 p-5 dark:border-violet-900 dark:bg-violet-950/20"><p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">Quick Check</p><div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-bold">{lesson.quick_check.title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{lesson.quick_check.question_count} questions. Use this to check what stuck.</p></div><Link className="btn-primary shrink-0" to={`/learning-v2/modules/${moduleKey}/assessments/${lesson.quick_check.key}`}>{["completed", "passed"].includes(lesson.quick_check.progress.status) ? "Try again" : "Start Quick Check"}</Link></div></section> : null}
    <div className="sticky bottom-4 z-10 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/95"><div className="flex flex-wrap items-center justify-between gap-3"><Link className="btn-secondary" to={`/learning-v2/modules/${moduleKey}`}>Back to module</Link><div className="flex flex-wrap gap-2">{data.previous_lesson_key ? <Link className="btn-secondary inline-flex items-center gap-2" to={lessonRoute(data.previous_lesson_key)}><ArrowLeft size={16} aria-hidden="true" />Previous lesson</Link> : null}<button className="btn-secondary" disabled={busy || completed} onClick={markComplete} type="button">{completed ? "Completed" : busy ? "Saving..." : "Mark lesson complete"}</button>{data.next_lesson_key ? <Link className="btn-primary inline-flex items-center gap-2" to={lessonRoute(data.next_lesson_key)}>Next lesson<ArrowRight size={16} aria-hidden="true" /></Link> : <Link className="btn-primary" to={`/learning-v2/modules/${moduleKey}`}>Continue</Link>}</div></div></div>
  </main>;
}
