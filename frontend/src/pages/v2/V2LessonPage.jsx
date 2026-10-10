import { ArrowLeft, ArrowRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";
import LessonLayout from "../../components/academy/LessonLayout";
import V2Interaction from "../../components/v2/V2Interaction";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2ResourceCard from "../../components/v2/V2ResourceCard";
import V2Status from "../../components/v2/V2Status";
import V2NextStep from "../../components/v2/V2NextStep";
import { getCurrentStudent } from "../../hooks/useAuth";
import { completeV2Lesson, getV2Lesson, getV2Module } from "../../services/api";

const markdownComponents = {
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>,
  table: ({ children }) => <div className="overflow-x-auto"><table>{children}</table></div>,
};
const done = status => ["completed", "passed"].includes(status);

export default function V2LessonPage() {
  const { moduleKey, lessonKey } = useParams();
  return <V2LessonContent key={`${getCurrentStudent()?.id}:${moduleKey}:${lessonKey}`} moduleKey={moduleKey} lessonKey={lessonKey} />;
}

function V2LessonContent({ moduleKey, lessonKey }) {
  const [data, setData] = useState(null);
  const [moduleData, setModuleData] = useState(null);
  const [catalogError, setCatalogError] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(false);
  const load = useCallback(() => {
    setError("");
    return getV2Lesson(moduleKey, lessonKey, { suppressToast: true }).then(res => { if (alive.current) setData(res.data); }).catch(err => { if (alive.current) setError(err?.response?.status === 404 ? "That lesson could not be found." : err?.userMessage || "The lesson could not be loaded."); });
  }, [lessonKey, moduleKey]);
  const loadCatalog = useCallback(() => {
    setCatalogError(false);
    return getV2Module(moduleKey, { suppressToast: true }).then(res => { if (alive.current) setModuleData(res.data); }).catch(() => { if (alive.current) setCatalogError(true); });
  }, [moduleKey]);
  useEffect(() => { alive.current = true; void load(); void loadCatalog(); return () => { alive.current = false; }; }, [load, loadCatalog]);
  async function refresh() { await Promise.all([load(), loadCatalog()]); }
  async function markComplete() {
    if (busy) return;
    setBusy(true); setError("");
    try { await completeV2Lesson(moduleKey, lessonKey, { suppressToast: true }); if (alive.current) await refresh(); }
    catch (err) { if (alive.current) setError(err?.userMessage || "We couldn't save lesson completion. Your work is still here. Try again."); }
    finally { if (alive.current) setBusy(false); }
  }
  if (error && !data) return <V2Error title="Lesson unavailable" message={error} onRetry={load} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  if (!data) return <V2Loading text="Loading lesson..." />;
  const lesson = data.lesson;
  const beginner = data.certification.version?.key === "nexus_beginner_aplus_v1";
  const status = beginner ? lesson.group_status || lesson.progress.status : lesson.progress.status;
  const completed = done(status);
  const resources = lesson.resources || [];
  const featured = resources.find(resource => resource.type === "video" && resource.url) || resources.find(resource => resource.url);
  const lessonRoute = key => `/learning-v2/modules/${moduleKey}/lessons/${key}`;
  const catalog = moduleData?.lessons?.map(item => ({ key: item.key, title: item.title, route: lessonRoute(item.key), current: item.key === lessonKey, complete: done(beginner ? item.group_status || item.progress?.status : item.progress?.status), available: item.available !== false && !item.locked, minutes: item.estimated_minutes }));
  const steps = [
    { id: "lesson-understand", label: "Understand" },
    ...(resources.length ? [{ id: "lesson-resources", label: featured?.type === "video" ? "Watch the video" : "Teaching resources", complete: resources.filter(item => item.required).length > 0 && resources.filter(item => item.required).every(item => item.exposure_satisfied === true || item.watched_at || item.type !== "video" && item.opened_at) }] : []),
    ...(data.interactions?.length ? [{ id: "lesson-practice", label: "Try it", complete: data.interactions.filter(item => item.interaction.required).length > 0 && data.interactions.filter(item => item.interaction.required).every(item => item.progress.passed) }] : []),
    ...(lesson.quick_check ? [{ id: "lesson-checkpoint", label: "Quick Check", complete: done(lesson.quick_check.progress.status) }] : []),
    { id: "lesson-completion", label: completed ? "Lesson done" : "Continue learning", complete: completed },
  ];
  return <LessonLayout title={lesson.title} summary={lesson.summary}
    breadcrumb={<nav className="breadcrumb" aria-label="Breadcrumb"><Link to="/learning-v2">My Course</Link><span aria-hidden="true">›</span><Link to={`/learning-v2/modules/${moduleKey}`}>{data.module.title}</Link></nav>}
    meta={<>{lesson.estimated_minutes ? <span className="small muted">About {lesson.estimated_minutes} min</span> : null}<V2Status status={status} /></>}
    steps={steps} resources={resources.length > 0} practice={data.interactions?.length > 0} catalog={catalog} catalogTitle="Module lessons" catalogError={catalogError} retryCatalog={loadCatalog}
    footer={<>{data.previous_lesson_key ? <Link className="btn btn-secondary" to={lessonRoute(data.previous_lesson_key)}><ArrowLeft size={16} aria-hidden="true" />Previous lesson</Link> : <Link className="btn btn-secondary" to={`/learning-v2/modules/${moduleKey}`}><ArrowLeft size={16} aria-hidden="true" />Back to module</Link>}<a className="btn btn-primary" href="#lesson-completion">Your next step<ArrowRight size={16} aria-hidden="true" /></a></>}>
    {featured ? <div className="lesson-anchor" id="lesson-resources" tabIndex={-1}><V2ResourceCard key={featured.key} resource={featured} moduleKey={moduleKey} onChanged={refresh} lessonPoster /></div> : null}
    <section className="card" id="lesson-understand" tabIndex={-1} aria-labelledby="lesson-content-title"><h2 id="lesson-content-title">Understand</h2>
      {lesson.objectives?.length ? <><h3>In this lesson, you'll learn</h3><ul className="lesson-objectives">{lesson.objectives.map((objective, index) => <li key={`${objective.code}-${index}`}><span className="objective-number" aria-hidden="true">{index + 1}</span>{objective.text}{objective.code ? <small className="block muted">Objective {objective.code}</small> : null}</li>)}</ul></> : null}
      {lesson.content_markdown ? <article className="v2-markdown lesson-prose"><ReactMarkdown components={markdownComponents}>{lesson.content_markdown}</ReactMarkdown></article> : <p className="sub">No written material is available for this lesson. Review its resources and current requirements below.</p>}
    </section>
    {resources.some(resource => resource !== featured) ? <section id={featured ? undefined : "lesson-resources"} tabIndex={-1} aria-labelledby="resources-title" className="card"><h2 id="resources-title">Teaching resources</h2><p className="small sub">Opening a resource records a visit. Viewing alone does not mean you passed a check.</p>{resources.filter(resource => resource !== featured).map(resource => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={refresh} />)}</section> : null}
    {data.interactions?.length ? <section className="card" id="lesson-practice" tabIndex={-1} aria-labelledby="interactions-title"><h2 id="interactions-title">Try it</h2>{data.interactions.map(({ interaction, progress }) => <div className="embedded-practice" key={interaction.key}><V2Interaction moduleKey={moduleKey} interactionKey={interaction.key} embedded onChanged={refresh} /><Link className="btn-quiet mt-3" to={`/learning-v2/modules/${moduleKey}/interactions/${interaction.key}`}>{progress.passed ? "Practice again" : "Try interaction"} on its own page<ArrowRight size={15} aria-hidden="true" /></Link></div>)}</section> : null}
    {lesson.quick_check ? <section className="card" id="lesson-checkpoint" tabIndex={-1} aria-labelledby="quick-check-title"><div className="section-title"><h2 id="quick-check-title">{lesson.quick_check.title}</h2><V2Status status={lesson.quick_check.progress.status} /></div><p className="small sub">{lesson.quick_check.question_count} questions to check your understanding.</p>{lesson.quick_check.available === false ? <span className="small sub">Quick Check unavailable</span> : <Link className="btn btn-secondary" to={`/learning-v2/modules/${moduleKey}/assessments/${lesson.quick_check.key}`}>{done(lesson.quick_check.progress.status) ? "Try Quick Check again" : "Start Quick Check"}</Link>}</section> : null}
    {error ? <p className="card" role="alert">{error}</p> : null}
    <section className="card" id="lesson-completion" tabIndex={-1} aria-labelledby="lesson-next-title"><h2 id="lesson-next-title">{completed ? "Lesson done" : "Continue learning"}</h2>{beginner ? <V2NextStep key={`${status}-${resources.map(item => item.status).join("-")}-${data.interactions?.map(item => item.progress.status).join("-")}`} moduleKey={moduleKey} /> : <><p className="small sub">Lesson completion tracks navigation; checks and practice determine mastery.</p><div className="actions">{completed ? data.next_lesson_key ? <Link className="btn btn-primary" to={lessonRoute(data.next_lesson_key)}>Next lesson<ArrowRight size={16} aria-hidden="true" /></Link> : <Link className="btn btn-primary" to={`/learning-v2/modules/${moduleKey}`}>Back to module</Link> : <button className="btn btn-primary" disabled={busy} onClick={markComplete} type="button">{busy ? "Saving..." : "Mark lesson complete"}</button>}</div></>}</section>
  </LessonLayout>;
}
