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
  const current = data.current_week;
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
      <div><h1 className="text-3xl font-bold text-slate-950 dark:text-white">Progress</h1><p className="mt-1 text-slate-600 dark:text-slate-300">Review your weekly completion, scores, practice, rank, and capstone readiness.</p></div>
      <section className="rounded-2xl bg-slate-950 p-5 text-white dark:bg-blue-950 sm:p-7"><div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-semibold uppercase tracking-wide text-blue-300">Course progress</p><p className="mt-2 text-4xl font-bold">{data.overall_training.percent}%</p><p className="mt-2 text-sm text-slate-300">{data.overall_training.completed} of {data.overall_training.total} required activities complete</p>{current ? <p className="mt-3 text-sm text-white">Current: Week {current.week_number} — {current.title}</p> : null}</div><Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-white px-5 py-3 font-bold text-blue-700" to="/training">Continue Training</Link></div></section>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Metric label="Videos Watched" metric={data.videos} Icon={PlayCircle} /><Metric label="Quizzes Completed" metric={data.quizzes} Icon={Trophy} note={`Average quiz score: ${data.quizzes.average_score_percent ?? 0}% · Best quiz score: ${data.quizzes.best_score_percent ?? 0}%`} /><Metric label="Required Practice" metric={data.practice} Icon={FlaskConical} /><Metric label="Guided Labs" metric={data.guided_labs} Icon={CheckCircle2} /><Metric label="Tickets Completed" metric={data.tickets} Icon={Ticket} /><Metric label="Weeks Completed" metric={{ completed: data.weeks_completed, total: data.total_weeks, percent: data.total_weeks ? Math.round(data.weeks_completed / data.total_weeks * 100) : 0 }} Icon={Target} /></section>
      {serviceDeskSummary ? (
        <section className="panel">
          <h2 className="text-xl font-bold">Service Desk Simulator</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div><p className="text-sm text-slate-500 dark:text-slate-400">Tickets completed</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.tickets_completed}</p></div>
            <div><p className="text-sm text-slate-500 dark:text-slate-400">Achievements unlocked</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.achievements_unlocked}</p></div>
            <div><p className="text-sm text-slate-500 dark:text-slate-400">Total XP</p><p className="mt-1 text-2xl font-bold">{serviceDeskSummary.total_xp}</p></div>
          </div>
          {serviceDeskSummary.recent_activity?.length ? (
            <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Recent activity</h3>
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
        </section>
      ) : null}
      <section className="grid gap-4 md:grid-cols-2"><div className="panel"><div className="flex items-center gap-2"><Award className="text-violet-600" /><h2 className="text-xl font-bold">Rank Progress</h2></div><p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Current role: <strong>{data.rank_progress?.current_role?.name || data.rank_progress?.current_role || "Trainee"}</strong></p><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{data.rank_progress?.next_role ? `Next role: ${data.rank_progress.next_role.name || data.rank_progress.next_role}` : "Highest configured role reached"}</p></div><div className="panel"><h2 className="text-xl font-bold">Capstone Readiness</h2><p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{data.capstone_readiness?.available ? "You can access the capstones appropriate for your current role." : "Keep completing weekly requirements and role gates to unlock capstones."}</p><p className="mt-2 text-sm font-semibold text-blue-600 dark:text-blue-400">{data.capstone_readiness?.available || 0} of {data.capstone_readiness?.total || 0} available</p></div></section>
      <section><h2 className="text-xl font-bold">Weekly Roadmap</h2><div className="mt-3 space-y-2">{data.weekly_roadmap.map((week) => <Link key={week.id} to={week.locked ? "/progress" : `/training/week/${week.week_number}`} aria-disabled={week.locked} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"><div><p className="font-semibold">Week {week.week_number} — {week.title}</p><p className="text-xs text-slate-500">{week.required_complete} of {week.required_total} required</p></div><span className="text-sm font-bold text-slate-600 dark:text-slate-300">{week.locked ? "Locked" : week.is_complete ? "Complete" : `${week.completion_percent}%`}</span></Link>)}</div></section>
    </main>
  );
}
