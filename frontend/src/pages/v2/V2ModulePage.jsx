import { ArrowRight, BookOpen, Brain, BriefcaseBusiness, FlaskConical, HelpCircle, MessageSquareText, Ticket } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2Status from "../../components/v2/V2Status";
import { getV2Module } from "../../services/api";

function AssessmentCard({ item, moduleKey, Icon, action, route }) {
  return <div className="panel flex min-h-40 flex-col">
    <div className="flex items-start justify-between gap-3"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"><Icon size={21} aria-hidden="true" /></span><V2Status status={item.progress.status} /></div>
    <h3 className="mt-4 font-bold text-slate-950 dark:text-white">{item.title}</h3>
    {item.question_count ? <p className="mt-1 text-sm text-slate-500">{item.question_count} questions · {item.pass_percent}% to pass</p> : null}
    {item.available && route ? <Link className="mt-auto pt-4 text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to={route(item, moduleKey)}>{action} →</Link> : <p className="mt-auto pt-4 text-sm text-slate-500">Unavailable in this development environment</p>}
  </div>;
}

export default function V2ModulePage() {
  const { moduleKey } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => { setError(""); getV2Module(moduleKey, { suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.response?.status === 404 ? "That module could not be found." : err?.userMessage || "The module could not be loaded.")); }, [moduleKey]);
  useEffect(load, [load]);
  if (error) return <V2Error title="Module unavailable" message={error} onRetry={load} />;
  if (!data) return <V2Loading text="Loading module..." />;
  const byRole = (role) => data.assessments.find((item) => item.role === role);
  const moduleQuiz = byRole("module_quiz");
  const practical = byRole("practical");
  const serviceDesk = byRole("service_desk");
  const examCode = data.certification.version.exam_codes?.[0];
  return <main className="mx-auto max-w-6xl space-y-8 p-4 pb-20 sm:p-6">
    <V2Breadcrumbs certification={data.certification} module={data.module} />
    <header className="max-w-4xl">
      <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">{examCode} · {data.certification.domain?.title}</p>
      <h1 className="mt-2 text-3xl font-bold text-slate-950 dark:text-white sm:text-4xl">{data.module.title}</h1>
      <p className="mt-3 text-lg leading-8 text-slate-600 dark:text-slate-300">{data.module.description}</p>
      <Link className="btn-primary mt-6 inline-flex min-h-12 items-center gap-2" to={data.continue.route}>{data.continue.label}<ArrowRight size={18} aria-hidden="true" /></Link>
    </header>
    <section aria-labelledby="learn-heading">
      <div className="mb-4 flex items-center gap-3"><BookOpen className="text-blue-600" aria-hidden="true" /><div><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Learn</p><h2 id="learn-heading" className="text-2xl font-bold">Build the foundation</h2></div></div>
      <ol className="space-y-3">
        {data.lessons.map((lesson, index) => <li key={lesson.key}>
          <Link className="panel group flex items-center gap-4 p-4 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700" to={`/learning-v2/modules/${data.module.key}/lessons/${lesson.key}`}>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 font-bold text-slate-600 group-hover:bg-blue-100 group-hover:text-blue-700 dark:bg-slate-800 dark:text-slate-300">{index + 1}</span>
            <div className="min-w-0 flex-1"><h3 className="font-bold text-slate-950 dark:text-white">{lesson.title}</h3><p className="mt-1 text-sm text-slate-500">{lesson.estimated_minutes ? `About ${lesson.estimated_minutes} min` : "Lesson"}{lesson.importance === "job_critical" ? " · Useful on the job" : ""}</p></div>
            <V2Status status={lesson.progress.status} />
          </Link>
        </li>)}
      </ol>
    </section>
    <section aria-labelledby="apply-heading">
      <div className="mb-4 flex items-center gap-3"><Brain className="text-violet-600" aria-hidden="true" /><div><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Check → Practice → Troubleshoot → Explain</p><h2 id="apply-heading" className="text-2xl font-bold">Put it together</h2></div></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {moduleQuiz ? <AssessmentCard item={moduleQuiz} moduleKey={data.module.key} Icon={HelpCircle} action="Take the quiz" route={(item, key) => `/learning-v2/modules/${key}/assessments/${item.key}`} /> : null}
        {practical ? <AssessmentCard item={practical} moduleKey={data.module.key} Icon={FlaskConical} action="Open practical" route={(item, key) => `/learning-v2/modules/${key}/practical/${item.key}`} /> : null}
        {serviceDesk ? <AssessmentCard item={serviceDesk} moduleKey={data.module.key} Icon={Ticket} action="Troubleshoot a ticket" route={(item, key) => `/learning-v2/modules/${key}/service-desk/${item.key}`} /> : null}
        <div className="panel flex min-h-40 flex-col"><span className="w-fit rounded-xl bg-blue-50 p-2.5 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"><MessageSquareText size={21} aria-hidden="true" /></span><h3 className="mt-4 font-bold">Explain it in your own words</h3><p className="mt-1 text-sm text-slate-500">{data.progress.explain_prompts.completed} of {data.progress.explain_prompts.total} complete</p>{data.explain_prompts[0] ? <Link className="mt-auto pt-4 text-sm font-semibold text-blue-600 dark:text-blue-400" to={`/learning-v2/modules/${data.module.key}/explain/${data.explain_prompts.find((p) => !["completed", "passed"].includes(p.progress.status))?.key || data.explain_prompts[0].key}`}>Open Explain →</Link> : <p className="mt-auto pt-4 text-sm text-slate-500">No prompt available</p>}</div>
      </div>
    </section>
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Module progress">
      <div className="panel"><p className="text-sm text-slate-500">Lessons</p><p className="mt-1 text-xl font-bold">{data.progress.lessons.completed} / {data.progress.lessons.total}</p></div>
      <div className="panel"><p className="text-sm text-slate-500">Quick Checks</p><p className="mt-1 text-xl font-bold">{data.progress.quick_checks.completed} / {data.progress.quick_checks.total}</p></div>
      <div className="panel"><p className="text-sm text-slate-500">Module Quiz</p><p className="mt-1 text-xl font-bold">{data.progress.module_quiz?.activity?.score != null ? `${data.progress.module_quiz.activity.score}%${data.progress.module_quiz.activity.passed ? " ✓" : ""}` : "Not started"}</p></div>
      <div className="panel"><p className="text-sm text-slate-500">Practical</p><div className="mt-2"><V2Status status={data.progress.practical?.activity?.status} /></div></div>
      <div className="panel"><p className="text-sm text-slate-500">Service Desk</p><div className="mt-2"><V2Status status={data.progress.service_desk?.activity?.status} /></div></div>
      <div className="panel"><p className="text-sm text-slate-500">Explain</p><p className="mt-1 text-xl font-bold">{data.progress.explain_prompts.completed} / {data.progress.explain_prompts.total}</p></div>
    </section>
    <p className="sr-only"><BriefcaseBusiness />This module connects learning to workplace practice.</p>
  </main>;
}
