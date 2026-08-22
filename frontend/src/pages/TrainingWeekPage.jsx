import { Check, ChevronLeft, Clock, ExternalLink, Lock } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import TicketNoteExercise from "../components/TicketNoteExercise";
import TrainingSubnav from "../components/TrainingSubnav";
import { JOB_RELEVANCE_TAGS, JobRelevanceBadge } from "../components/ui/Badge";
import { getTrainingModule, getTrainingWeek, markTrainingVideoWatched } from "../services/api";

function ActivityCard({ activity, cliPracticeRoute, isNext = false, onWatched, returnTo }) {
  const quiz = activity.linked_quiz;
  const actionLabel = activity.complete ? "Review" : activity.status === "in_progress" ? "Continue" : "Start";
  const isWeekOneTicketLesson = activity.stable_id === "week-1-lesson-2";
  const isWeekOneCliLesson = activity.stable_id === "week-1-lesson-3";
  const isInlineWeekOneLesson = isWeekOneTicketLesson || isWeekOneCliLesson;
  return (
    <article id={activity.stable_id} data-activity-type={activity.activity_type} className={`rounded-xl border bg-white p-4 dark:bg-slate-900 ${isNext ? "border-blue-500 ring-2 ring-blue-100 dark:border-blue-400 dark:ring-blue-950" : "border-slate-200 dark:border-slate-700"}`}>
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 ${activity.complete ? "border-green-500 bg-green-500 text-white" : activity.status === "locked" ? "border-slate-300 text-slate-400 dark:border-slate-600" : "border-blue-300 text-blue-600 dark:border-blue-700"}`}>{activity.complete ? <Check size={16} /> : activity.status === "locked" ? <Lock size={14} /> : ""}</span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">{isNext ? <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[11px] font-bold uppercase text-white">Next</span> : null}<span className="text-xs font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400">{activity.activity_label}</span><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${activity.is_required ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" : "bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300"}`}>{activity.requirement_label}</span>{activity.activity_type === "video" ? <JobRelevanceBadge value={activity.job_relevance} /> : null}{activity.estimated_minutes ? <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Clock size={12} />{activity.estimated_minutes} min</span> : null}</div>
            <h3 className="mt-1 font-bold text-slate-900 dark:text-white">{activity.title}</h3>
            {activity.description ? <p className="mt-1 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{activity.description}</p> : null}
            {activity.score_percent != null ? <p className="mt-2 text-sm font-semibold text-green-700 dark:text-green-300">Quiz score: {activity.score}/{activity.total} ({activity.score_percent}%)</p> : null}
            {!activity.prerequisite_met ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">Recommended first: {activity.prerequisite_title}</p> : null}
            {activity.permission_reason ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">{activity.permission_reason}</p> : null}
            {isWeekOneTicketLesson ? <div className="mt-3 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300"><p>Internal notes record the technical evidence another technician needs, while user-facing updates explain the outcome in plain language. Keep those audiences separate so the user gets a clear resolution without internal troubleshooting shorthand. For example, an internal note can say “Ran <code>ipconfig /renew</code>; lease obtained at 10:14,” while the user-facing update says “Your connection is working again.” Use the exercise below to turn a vague note into an actionable one.</p><TicketNoteExercise /></div> : null}
            {isWeekOneCliLesson ? <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">Commands give technicians exact evidence: GUI status icons summarize, but command output is timestamped, copyable, and provable. That makes it stronger support-ticket evidence, especially in a remote session where the GUI may be unavailable.</p> : null}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 sm:max-w-xs sm:justify-end">
          {activity.activity_type === "video" && activity.external_url ? <a href={activity.external_url} target="_blank" rel="noreferrer" className="btn-secondary min-h-10">{activity.complete ? "Watch Again" : "Watch Video"}<ExternalLink size={14} /></a> : null}
          {activity.activity_type === "video" && !activity.complete ? <button type="button" onClick={() => onWatched(activity)} className="btn-secondary min-h-10">Mark Watched</button> : null}
          {quiz?.available ? <Link className="btn-secondary min-h-10" to={quiz.action === "review" ? quiz.review_route : quiz.route} state={{ returnTo }}>{quiz.action === "review" ? `Review Quiz${quiz.score_percent != null ? ` · ${quiz.score_percent}%` : ""}` : "Take Quiz"}</Link> : null}
          {isWeekOneCliLesson && cliPracticeRoute ? <Link className="btn-primary min-h-10" to={cliPracticeRoute} state={{ returnTo }}>Start CLI Practice</Link> : null}
          {!isInlineWeekOneLesson && activity.activity_type === "service_desk_scenario" && activity.destination_route ? <a className="btn-primary min-h-10" href={activity.destination_route}>{actionLabel}</a> : null}
          {!isInlineWeekOneLesson && activity.activity_type !== "video" && activity.activity_type !== "service_desk_scenario" && activity.destination_route ? <Link className="btn-primary min-h-10" to={activity.destination_route} state={{ returnTo }}>{actionLabel}</Link> : null}
        </div>
      </div>
    </article>
  );
}

function ActivitySection({ cliPracticeRoute, description, items, nextId, onWatched, returnTo, title }) {
  if (!items.length) return null;
  return <section className="space-y-3"><div><h2 className="text-2xl font-bold text-slate-950 dark:text-white">{title}</h2><p className="text-sm text-slate-600 dark:text-slate-300">{description}</p></div>{items.map((item) => <ActivityCard key={item.id} activity={item} cliPracticeRoute={cliPracticeRoute} isNext={item.id === nextId} onWatched={onWatched} returnTo={returnTo} />)}</section>;
}

function normalizeModule(data) {
  if (data?.stable_id?.startsWith("module.")) return data;
  if (!data?.module) return null;
  return {
    ...data,
    stable_id: data.module.stable_id,
    stage_id: data.module.stage_id,
    title: data.module.title,
    purpose: data.module.purpose,
    route: data.module.route,
    learning_outcomes: data.learning_goals || [],
  };
}

export default function TrainingWeekPage() {
  const { moduleId, weekId } = useParams();
  const location = useLocation();
  const [module, setModule] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    const request = moduleId ? getTrainingModule(moduleId, { suppressToast: true }) : getTrainingWeek(weekId, { suppressToast: true });
    return request.then((res) => {
      const normalized = normalizeModule(res.data);
      if (!normalized) throw new Error("Missing module mapping");
      setModule(normalized);
      setError("");
    }).catch((err) => setError(err?.response?.status === 403 ? (err?.userMessage || "This module is locked. Complete the current module first.") : "This training module could not be loaded."));
  }, [moduleId, weekId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const activityId = new URLSearchParams(location.search).get("activity");
    if (module && activityId) requestAnimationFrame(() => document.getElementById(activityId)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }, [location.search, module]);
  const handleWatched = async (activity) => {
    await markTrainingVideoWatched(activity.id);
    await load();
  };
  if (error) return <main className="mx-auto max-w-3xl p-6"><BackLink className="mb-4 inline-flex items-center gap-1 text-blue-600" fallbackLabel="Learning Path" fallbackTo="/learning-path" /><div role="alert" className="panel">{error}</div></main>;
  if (!module) return <main className="mx-auto max-w-5xl p-6"><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;
  const required = module.activities.filter((item) => item.is_required);
  const extra = module.activities.filter((item) => !item.is_required);
  const byRole = (role) => required.filter((item) => item.learning_role === role);
  const nextId = module.next_activity?.id;
  const returnTo = module.route;
  const cliPracticeRoute = module.activities.find((item) => item.stable_id === "week-1-networking_lab-meet-cli-001")?.destination_route;
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
      <Link className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to="/learning-path"><ChevronLeft size={16} />Learning Path</Link>
      <TrainingSubnav />
      <header className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 sm:p-7">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">{module.stage?.title || "Learning Path"} · Module</p><h1 className="mt-2 text-3xl font-bold text-slate-950 dark:text-white">{module.title}</h1><p className="mt-2 max-w-3xl text-slate-600 dark:text-slate-300">{module.purpose}</p>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end"><div><div className="mb-2 flex justify-between text-sm text-slate-600 dark:text-slate-300"><span>{module.required_complete} of {module.required_total} required complete{module.required_estimated_minutes ? ` · about ${Math.ceil(module.required_estimated_minutes / 60)} hr` : ""}</span><strong>{module.completion_percent}%</strong></div><div className="h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-full bg-blue-600" style={{ width: `${module.completion_percent}%` }} /></div></div>{module.next_activity?.destination_route ? module.next_activity.activity_type === "service_desk_scenario" ? <a className="btn-primary" href={module.next_activity.destination_route}>Continue Current Activity</a> : <Link className="btn-primary" to={module.next_activity.destination_route} state={{ returnTo }}>Continue Current Activity</Link> : null}</div>
        {module.learning_outcomes?.length ? <div className="mt-5"><h2 className="font-bold text-slate-900 dark:text-white">What you will learn</h2><ul className="mt-2 grid gap-2 text-sm text-slate-600 dark:text-slate-300 sm:grid-cols-2">{module.learning_outcomes.map((goal) => <li key={goal} className="flex gap-2"><Check size={15} className="mt-0.5 shrink-0 text-blue-600" />{goal}</li>)}</ul></div> : null}
      </header>
      <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-100"><strong>Your learning pattern:</strong> Learn → Check → Practice → Troubleshoot → Prove. This labels the kind of learning activity; competency evidence is still evaluated separately.</div>
      {byRole("learn").some((item) => item.activity_type === "video") ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
          <span className="font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Video importance:</span>
          {Object.keys(JOB_RELEVANCE_TAGS).map((key) => (
            <span key={key} className="inline-flex items-center gap-1.5">
              <JobRelevanceBadge value={key} />
              {key === "job_critical" ? "comfortable using/explaining on the job" : key === "know_it" ? "recall for troubleshooting/interviews" : "recognize the concept"}
            </span>
          ))}
        </div>
      ) : null}
      <ActivitySection title="1. Learn" description="Build the core knowledge for this module." items={byRole("learn")} nextId={nextId} onWatched={handleWatched} returnTo={returnTo} cliPracticeRoute={cliPracticeRoute} />
      <ActivitySection title="2. Check" description="Check your understanding and review the explanations." items={byRole("check")} nextId={nextId} onWatched={handleWatched} returnTo={returnTo} cliPracticeRoute={cliPracticeRoute} />
      <ActivitySection title="3. Practice" description="Use the concepts in a guided or hands-on exercise." items={byRole("practice")} nextId={nextId} onWatched={handleWatched} returnTo={returnTo} cliPracticeRoute={cliPracticeRoute} />
      <ActivitySection title="4. Troubleshoot" description="Apply a support process to a realistic problem." items={byRole("troubleshoot")} nextId={nextId} onWatched={handleWatched} returnTo={returnTo} cliPracticeRoute={cliPracticeRoute} />
      <ActivitySection title="5. Prove" description="Complete an integrated challenge or project when one is available." items={byRole("prove")} nextId={nextId} onWatched={handleWatched} returnTo={returnTo} cliPracticeRoute={cliPracticeRoute} />
      {extra.length ? <details className="rounded-2xl border border-violet-200 bg-violet-50/50 p-4 dark:border-violet-900 dark:bg-violet-950/10"><summary className="cursor-pointer font-bold text-violet-900 dark:text-violet-200">Optional practice ({extra.length}) <span className="ml-2 text-sm font-normal text-violet-700 dark:text-violet-300">Does not affect module completion</span></summary><div className="mt-4 space-y-3">{extra.map((item) => <ActivityCard key={item.id} activity={item} cliPracticeRoute={cliPracticeRoute} onWatched={handleWatched} returnTo={returnTo} />)}</div></details> : null}
      <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-900 dark:bg-blue-950/20"><h2 className="text-xl font-bold text-slate-950 dark:text-white">{module.is_complete ? "Module Complete" : "Module Progress"}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{module.required_complete} of {module.required_total} required activities complete</p>{module.next_activity?.destination_route ? module.next_activity.activity_type === "service_desk_scenario" ? <a className="btn-primary mt-4" href={module.next_activity.destination_route}>Continue Current Activity</a> : <Link className="btn-primary mt-4" to={module.next_activity.destination_route} state={{ returnTo }}>Continue Current Activity</Link> : <Link className="btn-primary mt-4" to="/learning-path">Return to Learning Path</Link>}</section>
    </main>
  );
}
