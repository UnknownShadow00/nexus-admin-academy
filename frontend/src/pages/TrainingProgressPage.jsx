import { Award, CheckCircle2, FlaskConical, PlayCircle, Target, Ticket, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getServiceDeskProgressSummary, getTrainingProgress } from "../services/api";

function Metric({ label, metric, Icon, note }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p><p className="mt-2 text-2xl font-bold text-slate-950 dark:text-white">{metric.completed} <span className="text-base font-medium text-slate-400">of {metric.total}</span></p></div><Icon className="text-blue-600 dark:text-blue-400" size={22} /></div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-full rounded-full bg-blue-600" style={{ width: `${metric.percent}%` }} /></div><p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{note || `${metric.percent}% complete`}</p>
    </div>
  );
}

function formatShortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

export default function TrainingProgressPage() {
  const [data, setData] = useState(null);
  const [serviceDeskSummary, setServiceDeskSummary] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getTrainingProgress({ suppressToast: true }).then((res) => setData(res.data)).catch(() => setError("Progress could not be loaded.")); }, []);
  useEffect(() => {
    getServiceDeskProgressSummary({ suppressToast: true })
      .then((res) => setServiceDeskSummary(res.data))
      .catch(() => {});
  }, []);
  if (error) return <main className="mx-auto max-w-3xl p-6"><div role="alert" className="panel">{error}</div></main>;
  if (!data) return <main className="mx-auto max-w-5xl p-6"><div className="h-56 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;
  const current = data.current_module;
  return (
    <main className="mx-auto max-w-5xl space-y-8 p-4 pb-20 sm:p-6">
      <div><h1 className="text-3xl font-bold text-slate-950 dark:text-white">Skills</h1><p className="mt-1 text-slate-600 dark:text-slate-300">What you've completed, and where the evidence of real skill comes from.</p></div>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-950 dark:text-white">Training Progress</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">How much of the course you've completed — not yet a measure of independent skill.</p>
        </div>
        <div className="rounded-2xl bg-slate-950 p-5 text-white dark:bg-blue-950 sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-300">Course progress</p>
          <p className="mt-2 text-4xl font-bold">{data.overall_training.percent}%</p>
          <p className="mt-2 text-sm text-slate-300">{data.overall_training.completed} of {data.overall_training.total} required activities complete</p>
          {current ? <p className="mt-3 text-sm text-white">Current module: {current.title}</p> : null}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Metric label="Videos Watched" metric={data.videos} Icon={PlayCircle} /><Metric label="Quizzes Completed" metric={data.quizzes} Icon={Trophy} note={`Average quiz score: ${data.quizzes.average_score_percent ?? 0}% · Best quiz score: ${data.quizzes.best_score_percent ?? 0}%`} /><Metric label="Required Practice" metric={data.practice} Icon={FlaskConical} /><Metric label="Guided Labs" metric={data.guided_labs} Icon={CheckCircle2} /><Metric label="Tickets" metric={data.service_desk} Icon={Ticket} /><Metric label="Modules Completed" metric={{ completed: data.modules_completed, total: data.total_modules, percent: data.total_modules ? Math.round(data.modules_completed / data.total_modules * 100) : 0 }} Icon={Target} /></div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="panel"><div className="flex items-center gap-2"><Award className="text-violet-600" /><h3 className="text-lg font-bold">Rank Progress</h3></div><p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Current role: <strong>{data.rank_progress?.current_role?.name || data.rank_progress?.current_role || "Trainee"}</strong></p><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{data.rank_progress?.next_role ? `Next role: ${data.rank_progress.next_role.name || data.rank_progress.next_role}` : "Highest configured role reached"}</p></div>
          <div className="panel"><h3 className="text-lg font-bold">Capstone Readiness</h3><p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{data.capstone_readiness?.available ? "You can access the capstones appropriate for your current role." : "Keep completing module requirements and role gates to unlock capstones."}</p><p className="mt-2 text-sm font-semibold text-blue-600 dark:text-blue-400">{data.capstone_readiness?.available || 0} of {data.capstone_readiness?.total || 0} available</p></div>
        </div>
        <p className="text-sm"><Link className="font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to="/learning-path">View full learning path →</Link></p>
      </section>

      {serviceDeskSummary ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-white">Skill Evidence</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Based on tickets you've actually resolved — real evidence, not a completion count.</p>
          </div>
          <div className="panel">
            <h3 className="text-lg font-bold">Tickets</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div><p className="text-sm text-slate-500 dark:text-slate-400">Resolved</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.tickets_completed}</p></div>
              <div><p className="text-sm text-slate-500 dark:text-slate-400">Resolved first try</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.passed_first_try}</p></div>
              <div><p className="text-sm text-slate-500 dark:text-slate-400">Needed a second attempt</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.needed_revision}</p></div>
            </div>
            {serviceDeskSummary.skills?.length ? <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700"><h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Skills practiced</h4><div className="mt-2 flex flex-wrap gap-2">{serviceDeskSummary.skills.map((skill) => <span className="rounded-full bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-800 dark:bg-blue-950/30 dark:text-blue-200" key={skill.name}>{skill.name} · {skill.completed}</span>)}</div></div> : null}
            {serviceDeskSummary.needs_practice?.length ? <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20"><h4 className="font-semibold text-amber-900 dark:text-amber-200">Needs practice</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800 dark:text-amber-300">{serviceDeskSummary.needs_practice.map((title) => <li key={title}>{title}</li>)}</ul></div> : null}
            {serviceDeskSummary.recent_activity?.length ? (
              <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Recent activity</h4>
                <ul className="mt-2 divide-y divide-slate-200 dark:divide-slate-700">
                  {serviceDeskSummary.recent_activity.map((activity, index) => (
                    <li className="flex items-start justify-between gap-4 py-2" key={`${activity.created_at}-${index}`}>
                      <div><p className="font-medium">{activity.title}</p>{activity.detail ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{activity.detail}</p> : null}</div>
                      <time className="shrink-0 text-xs text-slate-500 dark:text-slate-400" dateTime={activity.created_at}>{formatShortDate(activity.created_at)}</time>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}
    </main>
  );
}
