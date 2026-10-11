import { BookOpen, Check, FileText, Link2, ListChecks } from "lucide-react";
import { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AcademyScene from "./AcademyScene";
import "./lesson.css";

// Navigation describes this page; only server evidence supplies completion.
export default function LessonLayout({ title, summary, breadcrumb, meta, steps, catalog, catalogTitle, catalogError, retryCatalog, notes, resources, practice, children, footer }) {
  const location = useLocation();
  const navigate = useNavigate();
  const requested = location.hash.slice(1);
  const active = steps.some(step => step.id === requested) ? requested : steps.find(step => step.id === "lesson-resources")?.id || steps[0]?.id;
  useEffect(() => {
    if (!requested || requested !== active) return;
    const target = document.getElementById(active);
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "start" });
  }, [active, requested, location.pathname]);
  const tabs = [["lesson-understand", "Learn", BookOpen], ...(notes ? [["lesson-notes", "My notes", FileText]] : []), ...(resources ? [["lesson-resources", "Resources", Link2]] : []), ...(practice ? [["lesson-practice", "Try it", ListChecks]] : [])];
  function follow(event, id) {
    const target = document.getElementById(id);
    if (!target) return;
    event.preventDefault();
    navigate({ pathname: location.pathname, search: location.search, hash: `#${id}` }, { preventScrollReset: true });
    target.focus({ preventScroll: true }); target.scrollIntoView({ block: "start" });
  }
  const completed = catalog?.filter(item => item.complete).length;
  const currentIndex = catalog?.findIndex(item => item.current);
  return <main className="academy-lesson">
    <div className="lesson-backdrop"><AcademyScene kind="backdrop" dark /><div className="lesson-backdrop-fade" /></div>
    <div className="learning-layout"><article className="stack lesson-main">
      <header className="card lesson-heading-card">
        {breadcrumb}
        <div className="lesson-heading"><div><h1>{title}</h1>{summary ? <p className="sub">{summary}</p> : null}</div><div className="lesson-meta">{currentIndex >= 0 ? <span className="small muted">Lesson {currentIndex + 1} of {catalog.length}</span> : null}{meta}</div></div>
        <nav className="lesson-tabs" aria-label="Lesson sections">{tabs.map(([id, label, Icon]) => <a key={id} className={`tab ${id === active ? "selected" : ""}`} href={`#${id}`} aria-current={active === id ? "location" : undefined} onClick={event => follow(event, id)}><Icon size={17} aria-hidden="true" />{label}</a>)}</nav>
      </header>
      {children}
      <div className="lesson-bottom">{footer}</div>
    </article><aside className="stack lesson-rail" aria-label="Lesson guide">
      <section className="card"><h2>Lesson steps</h2><ol className="lesson-steps">{steps.map((step, index) => <li key={step.id}><a className={active === step.id ? "active" : ""} href={`#${step.id}`} onClick={event => follow(event, step.id)} aria-current={active === step.id ? "location" : undefined}><span className={`step-number ${step.complete ? "complete" : ""}`}>{step.complete ? <Check size={14} aria-label="Complete" /> : index + 1}</span><span>{step.label}</span></a></li>)}</ol></section>
      {catalog?.length ? <section className="card lesson-catalog"><div className="section-title"><h2>{catalogTitle || "Module lessons"}</h2><span className="mono muted small">{completed} / {catalog.length}</span></div><div className="lesson-catalog-progress" role="progressbar" aria-label="Module lessons complete" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={catalog.length}><span style={{ width: `${completed / catalog.length * 100}%` }} /></div><ol className="lesson-list">{catalog.map((item, index) => <li key={item.key}>{item.available === false ? <span className="lesson-list-locked">{index + 1} · {item.title}<small>Locked</small></span> : <Link className={item.current ? "selected" : ""} to={item.route} aria-current={item.current ? "page" : undefined}><span>{index + 1} · {item.title}</span>{item.complete ? <Check size={16} aria-label="Complete" /> : item.minutes ? <span className="mono small">{item.minutes} min</span> : null}</Link>}</li>)}</ol></section> : catalogError ? <section className="card"><h2>Module lessons</h2><p className="small sub">The lesson list could not be loaded. Your lesson is still available.</p><button className="btn btn-secondary" type="button" onClick={retryCatalog}>Retry lesson list</button></section> : null}
      <section className="quote"><AcademyScene kind="quote" dark /><div className="quote-content"><div className="eyebrow">YOU CAN ALWAYS</div><p>Review the material · Retry practice · Go back to your course</p></div></section>
    </aside></div>
  </main>;
}
