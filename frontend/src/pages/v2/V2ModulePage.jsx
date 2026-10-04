import { ArrowRight, BookOpen, Brain, BriefcaseBusiness, FlaskConical, HelpCircle, MessageSquareText, Ticket } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2ResourceCard from "../../components/v2/V2ResourceCard";
import V2Status from "../../components/v2/V2Status";
import V2LockedActivity from "../../components/v2/V2LockedActivity";
import { getV2Module } from "../../services/api";
import { mentorFollowUpStatus, practicalDisplayStatus, stageProgressStatus } from "../../components/ui/statusFoundation";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";

function AssessmentCard({ item, moduleKey, Icon, action, route, beginner = false }) {
  if (!item.available || !route) return <V2LockedActivity activity={item} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  const displayStatus = item.role === "practical" ? practicalDisplayStatus(item.progress, beginner) : item.progress.status;
  const needsCorrection = displayStatus === "needs_correction";
  return <div className="panel flex min-h-40 flex-col">
    <div className="flex items-start justify-between gap-3"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"><Icon size={21} aria-hidden="true" /></span><V2Status status={displayStatus} /></div>
    <h3 className="mt-4 font-bold text-slate-950 dark:text-white">{item.title}</h3>
    {item.question_count ? <p className="mt-1 text-sm text-slate-500">{item.question_count} questions · {item.pass_percent}% to pass</p> : null}
    <Link className="mt-auto pt-4 text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to={route(item, moduleKey)}>{displayStatus === "awaiting_mentor_review" ? "View practical status" : needsCorrection ? "Fix & resubmit" : displayStatus === "approved" ? "Review practical" : action} →</Link>
  </div>;
}

export default function V2ModulePage() {
  const { moduleKey } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => { setError(""); return getV2Module(moduleKey, { suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.response?.status === 404 ? "That module could not be found." : err?.userMessage || "The module could not be loaded.")); }, [moduleKey]);
  useEffect(() => { void load(); }, [load]);
  if (error) return <V2Error title="Module unavailable" message={error} onRetry={load} />;
  if (!data) return <V2Loading text="Loading module..." />;
  const byRole = (role) => data.assessments.find((item) => item.role === role);
  const moduleQuiz = byRole("module_quiz");
  const practicals = data.assessments.filter((item) => item.role === "practical");
  const beginner = data.certification.version.key === "nexus_beginner_aplus_v1";
  const correction = practicals.find((item) => practicalDisplayStatus(item.progress, beginner) === "needs_correction");
  const serviceDesk = byRole("service_desk");
  const examCode = data.certification.version.exam_codes?.[0];
  const mentorStatus = beginner ? mentorFollowUpStatus(data.progress) : null;
  return <PageContainer className="space-y-8">
    <PageHeader
      breadcrumb={<V2Breadcrumbs certification={data.certification} module={data.module} />}
      eyebrow={`${beginner ? "Beginner A+ foundation" : examCode} · ${data.certification.domain?.title || "Course"}`}
      title={data.module.title}
      description={data.module.description}
      status={<><V2Status status={beginner ? stageProgressStatus(data.progress) : data.progress.status} />{mentorStatus ? <V2Status status={mentorStatus} /> : null}{data.progress.review_due ? <V2Status status="review_due" /> : null}</>}
      actions={<Link className="btn-primary min-h-12" to={data.continue.route}>{data.continue.kind === "review_pending" ? "View practical status" : data.continue.label}<ArrowRight size={18} aria-hidden="true" /></Link>}
    >
      {mentorStatus === "awaiting_mentor_review" ? <p className="mt-3 text-sm font-medium text-violet-900 dark:text-violet-200">Your practical is with your mentor.{data.continue.kind === "next_stage" ? " You can keep learning." : ""}</p> : null}
      {mentorStatus === "needs_correction" ? <p className="mt-3 text-sm font-medium text-amber-950 dark:text-amber-200">Your mentor requested changes to the practical. You can keep learning while you update it.{correction?.progress?.detail?.review_feedback ? ` Feedback: ${correction.progress.detail.review_feedback}` : ""}</p> : null}
    </PageHeader>
    <section aria-labelledby="learn-heading">
      <div className="mb-4 flex items-center gap-3"><BookOpen className="text-blue-600" aria-hidden="true" /><div><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Learn</p><h2 id="learn-heading" className="text-2xl font-bold">Build the foundation</h2></div></div>
      <ol className="space-y-3">
        {data.lessons.map((lesson, index) => <li key={lesson.key}>
          <Link className="panel group flex items-center gap-4 p-4 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700" to={`/learning-v2/modules/${data.module.key}/lessons/${lesson.key}`}>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 font-bold text-slate-600 group-hover:bg-blue-100 group-hover:text-blue-700 dark:bg-slate-800 dark:text-slate-300">{index + 1}</span>
            <div className="min-w-0 flex-1"><h3 className="font-bold text-slate-950 dark:text-white">{lesson.title}</h3><p className="mt-1 text-sm text-slate-500">{lesson.estimated_minutes ? `About ${lesson.estimated_minutes} min` : "Lesson"}{lesson.importance === "job_critical" ? " · Useful on the job" : ""}</p></div>
            <V2Status status={beginner ? lesson.group_status || lesson.progress.status : lesson.progress.status} />
          </Link>
        </li>)}
      </ol>
    </section>
    {data.interactions?.some(({ interaction }) => !interaction.lesson_key) ? <section className="panel space-y-3" aria-labelledby="module-interactions-title"><h2 className="text-xl font-bold" id="module-interactions-title">Module practice</h2><ul className="space-y-2">{data.interactions.filter(({ interaction }) => !interaction.lesson_key).map(({ interaction, progress }) => <li className="flex items-center justify-between gap-3" key={interaction.key}><span>{interaction.title} · {interaction.required ? "Required" : "Optional"}</span><Link className="font-semibold text-blue-700 underline dark:text-blue-300" to={`/learning-v2/modules/${moduleKey}/interactions/${interaction.key}`}>{progress.passed ? "Practice again" : "Try interaction"}</Link></li>)}</ul></section> : null}
    {data.module_resources?.length ? <section aria-labelledby="module-resources-heading" className="panel space-y-4"><div><p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Further practice</p><h2 id="module-resources-heading" className="mt-1 text-2xl font-bold">Module resources</h2><p className="mt-1 text-sm text-slate-500">Opening a link does not complete it or count as mastery.</p></div>{data.module_resources.map((resource) => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />)}</section> : null}
    <section aria-labelledby="apply-heading">
      <div className="mb-4 flex items-center gap-3"><Brain className="text-violet-600" aria-hidden="true" /><div><p className="text-xs font-bold uppercase tracking-wider text-slate-500">{beginner ? "Check → Practice → Apply" : "Check → Practice → Troubleshoot → Explain"}</p><h2 id="apply-heading" className="text-2xl font-bold">Put it together</h2></div></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {moduleQuiz ? <AssessmentCard item={moduleQuiz} moduleKey={data.module.key} Icon={HelpCircle} action="Take the quiz" route={(item, key) => `/learning-v2/modules/${key}/assessments/${item.key}`} /> : null}
        {practicals.map((item) => <AssessmentCard key={item.key} item={item} moduleKey={data.module.key} Icon={FlaskConical} action="Open practical" route={(assessment, key) => `/learning-v2/modules/${key}/practical/${assessment.key}`} beginner={beginner} />)}
        {serviceDesk ? <AssessmentCard item={serviceDesk} moduleKey={data.module.key} Icon={Ticket} action="Troubleshoot a ticket" route={(item, key) => `/learning-v2/modules/${key}/service-desk/${item.key}`} /> : null}
        {data.explain_prompts.length ? <div className="panel flex min-h-40 flex-col"><span className="w-fit rounded-xl bg-blue-50 p-2.5 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"><MessageSquareText size={21} aria-hidden="true" /></span><h3 className="mt-4 font-bold">Explain it in your own words</h3><p className="mt-1 text-sm text-slate-500">{data.progress.explain_prompts.completed} of {data.progress.explain_prompts.total} complete</p><Link className="mt-auto pt-4 text-sm font-semibold text-blue-600 dark:text-blue-400" to={`/learning-v2/modules/${data.module.key}/explain/${data.explain_prompts.find((p) => !["completed", "passed"].includes(p.progress.status))?.key || data.explain_prompts[0].key}`}>Open Explain →</Link></div> : null}
      </div>
    </section>
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label={beginner ? "Stage progress" : "Module progress"}>
      {!beginner ? <div className="panel"><p className="text-sm text-slate-500">Lessons</p><p className="mt-1 text-xl font-bold">{data.progress.lessons.completed} / {data.progress.lessons.total}</p></div> : null}
      <div className="panel"><p className="text-sm text-slate-500">Quick Checks</p><p className="mt-1 text-xl font-bold">{data.progress.quick_checks.completed} / {data.progress.quick_checks.total}</p></div>
      <div className="panel"><p className="text-sm text-slate-500">{beginner ? "Final checkpoint" : "Module Quiz"}</p><p className="mt-1 text-xl font-bold">{data.progress.module_quiz?.activity?.score != null ? `${data.progress.module_quiz.activity.score}%${data.progress.module_quiz.activity.passed ? " ✓" : ""}` : "Not started"}</p></div>
      {practicals.map((item) => <div className="panel" key={item.key}><p className="text-sm text-slate-600 dark:text-slate-300">{item.title}</p><div className="mt-2"><V2Status status={practicalDisplayStatus(item.progress, beginner)} /></div></div>)}
      {serviceDesk ? <div className="panel"><p className="text-sm text-slate-500">Service Desk</p><div className="mt-2"><V2Status status={data.progress.service_desk?.activity?.status} /></div></div> : null}
      {data.explain_prompts.length ? <div className="panel"><p className="text-sm text-slate-500">Explain</p><p className="mt-1 text-xl font-bold">{data.progress.explain_prompts.completed} / {data.progress.explain_prompts.total}</p></div> : null}
    </section>
    <p className="sr-only"><BriefcaseBusiness />This module connects learning to workplace practice.</p>
  </PageContainer>;
}
