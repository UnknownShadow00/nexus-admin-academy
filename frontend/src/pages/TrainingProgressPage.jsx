import { BookOpen, Brain, FlaskConical, Trophy } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AssessmentEvidence from "../components/AssessmentEvidence";
import ReviewEvidence from "../components/ReviewEvidence";
import { getDueFlashcards, getServiceDeskProgressSummary, getTrainingProgress } from "../services/api";

function Count({ label, completed, total = null, suffix = "complete" }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"><p className="text-sm font-medium text-slate-600 dark:text-slate-300">{label}</p><p className="mt-2 text-2xl font-bold text-slate-950 dark:text-white">{completed}{total !== null ? <span className="text-base font-medium text-slate-400"> / {total}</span> : null}</p><p className="mt-1 text-xs text-slate-500">{suffix}</p></div>;
}

function Group({ title, description, Icon, children, id }) {
  return <section className="space-y-4" id={id}><div className="flex items-start gap-3"><span className="rounded-lg bg-blue-50 p-2 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300"><Icon size={20} /></span><div><h2 className="text-xl font-bold text-slate-950 dark:text-white">{title}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{description}</p></div></div>{children}</section>;
}

export default function TrainingProgressPage() {
  const [data, setData] = useState(null);
  const [serviceDeskSummary, setServiceDeskSummary] = useState(null);
  const [serviceDeskError, setServiceDeskError] = useState(false);
  const [reviewSummary, setReviewSummary] = useState(null);
  const [reviewError, setReviewError] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [reviewReloadKey, setReviewReloadKey] = useState(0);

  const loadProgress = useCallback(() => {
    setError("");
    setData(null);
    getTrainingProgress({ suppressToast: true }).then((response) => setData(response.data)).catch(() => setError("Progress could not be loaded."));
    setServiceDeskError(false);
    getServiceDeskProgressSummary({ suppressToast: true }).then((response) => setServiceDeskSummary(response.data)).catch(() => { setServiceDeskSummary(null); setServiceDeskError(true); });
  }, []);

  useEffect(() => loadProgress(), [loadProgress, reloadKey]);
  useEffect(() => {
    setReviewError(false);
    setReviewSummary(null);
    getDueFlashcards({ suppressToast: true }).then((response) => setReviewSummary(response)).catch(() => setReviewError(true));
  }, [reviewReloadKey]);

  const attemptedAssessments = useMemo(() => (data?.assessments || []).filter((row) => row.latest_attempt || row.earned_pass).slice(0, 3), [data]);

  if (error) return <main className="mx-auto max-w-3xl p-6"><div className="panel" role="alert"><h1 className="font-bold">Progress is temporarily unavailable</h1><p className="mt-2">{error}</p><button className="btn-primary mt-4" onClick={() => setReloadKey((value) => value + 1)} type="button">Try again</button></div></main>;
  if (!data) return <main className="mx-auto max-w-5xl p-6" role="status"><div className="h-56 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;

  const evidence = data.evidence;
  const moduleEvidence = evidence.current_module;
  const current = data.current_module;
  const practical = evidence.practical;

  return (
    <main className="mx-auto max-w-5xl space-y-10 p-4 pb-20 sm:p-6">
      <header><p className="text-sm font-semibold text-blue-700 dark:text-blue-300">A+ Foundations</p><h1 className="mt-1 text-3xl font-bold text-slate-950 dark:text-white">Progress</h1><p className="mt-2 max-w-2xl text-slate-600 dark:text-slate-300">Completion, assessment results, and practical work are different kinds of evidence. No single percentage represents mastery or job readiness.</p></header>

      {!evidence.started ? <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-900 dark:bg-blue-950/20 sm:p-6"><p className="text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">You’re just getting started</p><h2 className="mt-2 text-2xl font-bold">Current: {current?.title || "Nexus Orientation"}</h2><p className="mt-2 text-slate-700 dark:text-slate-300">Your progress will build in three areas: learn the ideas, pass assessments independently, and practice the skills.</p><Link className="btn-primary mt-4 inline-flex" to={current?.route || "/learning-path"}>Continue learning</Link></section> : null}

      <section className="rounded-2xl bg-slate-950 p-5 text-white dark:bg-blue-950 sm:p-7"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">Current module</p><h2 className="mt-2 text-2xl font-bold">{current?.title || "A+ Foundations"}</h2><p className="mt-3 text-lg"><strong>{moduleEvidence.required.completed} of {moduleEvidence.required.total}</strong> required activities complete</p><div className="mt-5 grid gap-3 sm:grid-cols-3"><div><p className="text-sm text-slate-300">Lessons</p><p className="font-semibold">{moduleEvidence.lessons.completed} / {moduleEvidence.lessons.total} complete</p></div><div><p className="text-sm text-slate-300">Assessment</p><p className="font-semibold">{moduleEvidence.assessments.passed} / {moduleEvidence.assessments.total} passed</p></div><div><p className="text-sm text-slate-300">Practical</p><p className="font-semibold">{moduleEvidence.practical.completed} / {moduleEvidence.practical.total} complete</p></div></div><p className="mt-4 text-sm text-slate-300">Optional practice: {moduleEvidence.optional_practice.completed} completed · does not change required progress.</p>{current?.route ? <Link className="mt-4 inline-flex font-semibold text-blue-200 underline" to={current.route}>Open current module</Link> : null}</section>

      <Group title="Learning" description="A lesson complete means you explicitly finished it. It is not a mastery claim." Icon={BookOpen}><Count label="Required lessons" completed={evidence.learning.lessons_completed} total={evidence.learning.lessons_required} />{evidence.practice.completed ? <p className="text-sm text-slate-600 dark:text-slate-300">Practice completed: {evidence.practice.completed}. Practice helps you learn and does not award assessment credit.</p> : null}</Group>

      <Group title="Assessments" description="A passed assessment shows you met its threshold independently; it does not by itself prove job competence." Icon={Trophy}><Count label="Required assessments passed" completed={evidence.assessments.required_assessments_passed} total={evidence.assessments.required_assessments_total} suffix="passed" />{attemptedAssessments.length ? <AssessmentEvidence assessments={attemptedAssessments} /> : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">No assessment evidence recorded yet.</p>}</Group>

      <Group title="Practical work" description="Guided work and independent demonstrations stay separate." Icon={FlaskConical}><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Count label="Guided practice" completed={practical.guided_completed} total={practical.guided_total} /><Count label="Independent demonstrations" completed={practical.independent_completed} total={practical.independent_total} suffix="recorded" /><Count label="Service Desk tickets passed" completed={serviceDeskSummary?.tickets_completed || practical.tickets_passed} suffix="met the ticket rubric" /></div>{practical.historical_unclassified_total ? <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">Historical practical work without assistance-level evidence: {practical.historical_unclassified_completed} completed. Nexus does not label these records independent.</p> : null}{serviceDeskError ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">Service Desk evidence is temporarily unavailable; other progress remains visible.</p> : null}</Group>

      <Group id="review" title="Review" description="A small set of deterministic priorities from recent misses and scheduled reinforcement." Icon={Brain}><ReviewEvidence summary={reviewSummary} error={reviewError} onRetry={() => setReviewReloadKey((value) => value + 1)} /></Group>

      <details className="panel"><summary className="cursor-pointer font-semibold">Course totals and planned certifications</summary><div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300"><p><strong>Course required activities:</strong> {evidence.course_required_activities.completed} / {evidence.course_required_activities.total}</p><p><strong>Current:</strong> A+ Foundations</p><p><strong>Planned later:</strong> Network+, ITIL 4, Security+, Linux Essentials, AZ-900, AZ-104.</p><p>These later paths are plans, not completed or validated readiness claims.</p><Link className="font-semibold text-blue-600 dark:text-blue-400" to="/learning-path">View full learning path →</Link></div></details>
    </main>
  );
}
