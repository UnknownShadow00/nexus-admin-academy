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
  return <PageContainer width="reading" className="space-y-8">
    <PageHeader breadcrumb={<V2Breadcrumbs certification={data.certification} module={data.module} lesson={lesson} />} eyebrow="Lesson" title={lesson.title} description={lesson.summary} status={<V2Status status={beginner ? lesson.group_status || lesson.progress.status : lesson.progress.status} />} />
    <section aria-labelledby="lesson-content-title" className="learning-section">
      <p className="type-label">Learn</p><h2 id="lesson-content-title" className="learning-section-title">Work through the lesson</h2>
      <article className="v2-markdown learning-prose"><ReactMarkdown components={markdownComponents}>{lesson.content_markdown}</ReactMarkdown></article>
    </section>
    {lesson.resources.length ? <section aria-labelledby="resources-title" className="learning-section space-y-4"><div><p className="type-label">Reference</p><h2 id="resources-title" className="learning-section-title">Teaching resources</h2><p className="type-meta mt-1">Opening a resource records a visit. Viewing alone does not mean you passed a check.</p></div>{lesson.resources.map((resource) => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />)}</section> : null}
    {data.interactions?.length ? <section className="learning-section space-y-4" aria-labelledby="interactions-title"><div><p className="type-label">Try it</p><h2 className="learning-section-title" id="interactions-title">Check your understanding</h2></div><ul className="divide-y divide-[var(--nexus-border)]">{data.interactions.map(({ interaction, progress }) => <li className="flex flex-wrap items-center justify-between gap-3 py-4" key={interaction.key}><div><strong>{interaction.title}</strong><p className="type-meta mt-1">{interaction.required ? "Required" : "Optional"} · {statusLabel(progress.status)}</p></div><Link className="btn-secondary" to={`/learning-v2/modules/${moduleKey}/interactions/${interaction.key}`}>{progress.passed ? "Practice again" : "Try interaction"}</Link></li>)}</ul></section> : null}
    {lesson.quick_check ? <section className="learning-section space-y-3" aria-labelledby="quick-check-title"><p className="type-label">Checkpoint</p><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 id="quick-check-title" className="learning-section-title">{lesson.quick_check.title}</h2><p className="type-meta mt-1">{lesson.quick_check.question_count} questions to check your understanding.</p></div>{lesson.quick_check.available === false ? <span className="type-meta">Quick Check unavailable</span> : <Link className="btn-secondary" to={`/learning-v2/modules/${moduleKey}/assessments/${lesson.quick_check.key}`}>{["completed", "passed"].includes(lesson.quick_check.progress.status) ? "Try Quick Check again" : "Start Quick Check"}</Link>}</div></section> : null}
    {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200" role="alert">{error}</p> : null}
    <section className="learning-completion" aria-labelledby="lesson-next-title"><p className="type-label">Next action</p><h2 className="learning-section-title" id="lesson-next-title">{completed ? "Lesson done" : "Continue learning"}</h2>{beginner ? <div className="mt-3"><V2NextStep key={`${lesson.group_status || lesson.progress.status}-${lesson.resources.map((item) => item.status).join("-")}`} moduleKey={moduleKey} /></div> : <><p className="type-meta mt-2">Lesson completion tracks navigation; checks and practice determine mastery.</p><div className="mt-4 flex flex-wrap items-center gap-3">{completed ? (data.next_lesson_key ? <Link className="btn-primary" to={lessonRoute(data.next_lesson_key)}>Next lesson<ArrowRight size={16} aria-hidden="true" /></Link> : <Link className="btn-primary" to={`/learning-v2/modules/${moduleKey}`}>Back to module</Link>) : <button className="btn-primary" disabled={busy} onClick={markComplete} type="button">{busy ? "Saving..." : "Mark lesson complete"}</button>}{data.previous_lesson_key ? <Link className="btn-quiet" to={lessonRoute(data.previous_lesson_key)}><ArrowLeft size={16} aria-hidden="true" />Previous lesson</Link> : null}</div></>}</section>
  </PageContainer>;
}
