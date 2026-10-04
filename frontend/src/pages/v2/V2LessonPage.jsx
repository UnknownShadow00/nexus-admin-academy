import { ArrowLeft, ArrowRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2ResourceCard from "../../components/v2/V2ResourceCard";
import V2Status, { statusLabel } from "../../components/v2/V2Status";
import V2NextStep from "../../components/v2/V2NextStep";
import { completeV2Lesson, getV2Lesson } from "../../services/api";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";

const markdownComponents = {
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>,
  table: ({ children }) => <div className="overflow-x-auto"><table>{children}</table></div>,
};

export default function V2LessonPage() {
  const { moduleKey, lessonKey } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { setError(""); return getV2Lesson(moduleKey, lessonKey, { suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.response?.status === 404 ? "That lesson could not be found." : err?.userMessage || "The lesson could not be loaded.")); }, [lessonKey, moduleKey]);
  useEffect(() => { void load(); }, [load]);
  async function markComplete() { setBusy(true); setError(""); try { await completeV2Lesson(moduleKey, lessonKey, { suppressToast: true }); await load(); } catch (err) { setError(err?.userMessage || "We couldn't save lesson completion. Your work is still here. Try again."); } finally { setBusy(false); } }
  if (error && !data) return <V2Error title="Lesson unavailable" message={error} onRetry={load} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  if (!data) return <V2Loading text="Loading lesson..." />;
  const lesson = data.lesson;
  const beginner = data.certification.version?.key === "nexus_beginner_aplus_v1";
  const completed = ["completed", "passed"].includes(beginner ? lesson.group_status || lesson.progress.status : lesson.progress.status);
  const lessonRoute = (key) => `/learning-v2/modules/${moduleKey}/lessons/${key}`;
  return <PageContainer width="reading" className="space-y-6">
    <PageHeader breadcrumb={<V2Breadcrumbs certification={data.certification} module={data.module} lesson={lesson} />} title={lesson.title} description={lesson.summary} status={<><V2Status status={beginner ? lesson.group_status || lesson.progress.status : lesson.progress.status} />{lesson.importance === "job_critical" ? <span className="status-tone status-tone-neutral rounded-full px-2.5 py-1 text-xs font-semibold">Useful on the job</span> : null}</>}><p className="type-meta mt-2">About {lesson.estimated_minutes || "a few"} minutes</p></PageHeader>
    <article className="panel v2-markdown max-w-none"><ReactMarkdown components={markdownComponents}>{lesson.content_markdown}</ReactMarkdown></article>
    <section aria-labelledby="resources-title" className="panel space-y-4"><div><p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Watch / read</p><h2 id="resources-title" className="mt-1 text-2xl font-bold">Lesson resources</h2><p className="mt-1 text-sm text-slate-500">Opening a resource records a visit. “I watched this” records your report of viewing; checks and practice determine mastery.</p></div>{lesson.resources.length ? lesson.resources.map((resource) => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800">No resources are mapped to this lesson.</p>}</section>
    {data.interactions?.length ? <section className="panel space-y-4" aria-labelledby="interactions-title"><div><p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">Interact</p><h2 className="mt-1 text-2xl font-bold" id="interactions-title">Try it yourself</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">These activities check what you can recall or do. You can retry without penalty.</p></div><ul className="space-y-3">{data.interactions.map(({ interaction, progress }) => <li className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700" key={interaction.key}><div><strong>{interaction.title}</strong><p className="text-sm text-slate-600 dark:text-slate-300">{interaction.required ? "Required" : "Optional"} · {statusLabel(progress.status)}</p></div><Link className="btn-secondary" to={`/learning-v2/modules/${moduleKey}/interactions/${interaction.key}`}>{progress.passed ? "Practice again" : "Start interaction"}</Link></li>)}</ul></section> : null}
    {lesson.quick_check ? <section className="rounded-2xl border border-violet-200 bg-violet-50 p-5 dark:border-violet-900 dark:bg-violet-950/20"><p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">Quick Check</p><div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-bold">{lesson.quick_check.title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{lesson.quick_check.question_count} questions. Use this to check what stuck.</p></div>{lesson.quick_check.available === false ? <span className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">Quick Check unavailable</span> : <Link className="btn-primary shrink-0" to={`/learning-v2/modules/${moduleKey}/assessments/${lesson.quick_check.key}`}>{["completed", "passed"].includes(lesson.quick_check.progress.status) ? "Try again" : "Start Quick Check"}</Link>}</div></section> : null}
    {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200" role="alert">{error}</p> : null}
    {beginner ? <div className="lesson-sticky-actions"><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600 dark:text-slate-300">Open the teaching card, try the interaction, then pass the checkpoint. Reading alone does not master this stage.</p><V2NextStep key={`${lesson.group_status || lesson.progress.status}-${lesson.resources.map((item) => item.status).join("-")}`} moduleKey={moduleKey} /></div></div> : <div className="lesson-sticky-actions"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex flex-wrap gap-2"><Link className="btn-quiet" to={`/learning-v2/modules/${moduleKey}`}>Back to module</Link>{data.previous_lesson_key ? <Link className="btn-quiet" to={lessonRoute(data.previous_lesson_key)}><ArrowLeft size={16} aria-hidden="true" />Previous lesson</Link> : null}</div><div className="flex flex-wrap items-center gap-2"><span className="type-meta">Lesson completion tracks navigation only; checks and practice determine mastery.</span>{completed ? <span className="status-tone status-tone-success rounded-lg px-4 py-2 text-sm font-semibold">Lesson marked complete</span> : <button className="btn-primary" disabled={busy} onClick={markComplete} type="button">{busy ? "Saving..." : "Mark lesson complete"}</button>}{completed ? (data.next_lesson_key ? <Link className="btn-primary" to={lessonRoute(data.next_lesson_key)}>Next lesson<ArrowRight size={16} aria-hidden="true" /></Link> : <Link className="btn-primary" to={`/learning-v2/modules/${moduleKey}`}>Continue</Link>) : null}</div></div></div>}
  </PageContainer>;
}
