import { ArrowLeft, ArrowRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2ResourceCard from "../../components/v2/V2ResourceCard";
import V2Status from "../../components/v2/V2Status";
import { completeV2Lesson, getV2Lesson } from "../../services/api";

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
  async function markComplete() { setBusy(true); setError(""); try { await completeV2Lesson(moduleKey, lessonKey, { suppressToast: true }); await load(); } catch (err) { setError(err?.userMessage || "We couldn't save lesson completion. Your work is still here. Try again."); } finally { setBusy(false); } }
  if (error && !data) return <V2Error title="Lesson unavailable" message={error} onRetry={load} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  if (!data) return <V2Loading text="Loading lesson..." />;
  const lesson = data.lesson;
  const completed = ["completed", "passed"].includes(lesson.progress.status);
  const lessonRoute = (key) => `/learning-v2/modules/${moduleKey}/lessons/${key}`;
  return <main className="mx-auto max-w-5xl space-y-6 p-4 pb-24 sm:p-6">
    <V2Breadcrumbs certification={data.certification} module={data.module} lesson={lesson} />
    <header className="max-w-3xl"><div className="flex flex-wrap items-center gap-2"><V2Status status={lesson.progress.status} />{lesson.importance === "job_critical" ? <span className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-950/30 dark:text-violet-300">Useful on the job</span> : null}</div><h1 className="mt-4 text-3xl font-bold text-slate-950 dark:text-white sm:text-4xl">{lesson.title}</h1>{lesson.summary ? <p className="mt-3 text-lg text-slate-600 dark:text-slate-300">{lesson.summary}</p> : null}<p className="mt-2 text-sm text-slate-500">About {lesson.estimated_minutes || "a few"} minutes</p></header>
    <article className="panel v2-markdown max-w-none"><ReactMarkdown components={markdownComponents}>{lesson.content_markdown}</ReactMarkdown></article>
    <section aria-labelledby="resources-title" className="panel space-y-4"><div><p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Watch / read</p><h2 id="resources-title" className="mt-1 text-2xl font-bold">Lesson resources</h2><p className="mt-1 text-sm text-slate-500">Opening a link does not complete it. Mark it complete after you finish.</p></div>{lesson.resources.length ? lesson.resources.map((resource) => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800">No resources are mapped to this lesson.</p>}</section>
    {lesson.quick_check ? <section className="rounded-2xl border border-violet-200 bg-violet-50 p-5 dark:border-violet-900 dark:bg-violet-950/20"><p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">Quick Check</p><div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-bold">{lesson.quick_check.title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{lesson.quick_check.question_count} questions. Use this to check what stuck.</p></div>{lesson.quick_check.available === false ? <span className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">Quick Check unavailable</span> : <Link className="btn-primary shrink-0" to={`/learning-v2/modules/${moduleKey}/assessments/${lesson.quick_check.key}`}>{["completed", "passed"].includes(lesson.quick_check.progress.status) ? "Try again" : "Start Quick Check"}</Link>}</div></section> : null}
    {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200" role="alert">{error}</p> : null}
    <div className="sticky bottom-4 z-10 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/95"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex flex-wrap gap-2"><Link className="px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200" to={`/learning-v2/modules/${moduleKey}`}>Back to module</Link>{data.previous_lesson_key ? <Link className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200" to={lessonRoute(data.previous_lesson_key)}><ArrowLeft size={16} aria-hidden="true" />Previous lesson</Link> : null}</div><div className="flex flex-wrap gap-2">{completed ? <span className="inline-flex items-center rounded-lg bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">✓ Completed</span> : <button className="btn-primary" disabled={busy} onClick={markComplete} type="button">{busy ? "Saving..." : "Mark lesson complete"}</button>}{completed ? (data.next_lesson_key ? <Link className="btn-primary inline-flex items-center gap-2" to={lessonRoute(data.next_lesson_key)}>Next lesson<ArrowRight size={16} aria-hidden="true" /></Link> : <Link className="btn-primary" to={`/learning-v2/modules/${moduleKey}`}>Continue</Link>) : null}</div></div></div>
  </main>;
}
