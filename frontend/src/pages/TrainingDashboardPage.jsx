import { ArrowRight, Check, ChevronRight, Clock, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import TrainingSubnav from "../components/TrainingSubnav";
import { getTrainingDashboard } from "../services/api";

const statusLabels = { not_started: "Not Started", in_progress: "In Progress", complete: "Complete", locked: "Locked" };

function LoadingState() {
  return <main className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6"><div className="h-12 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" /><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;
}

export default function TrainingDashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getTrainingDashboard({ suppressToast: true })
      .then((response) => active && setData(response.data))
      .catch(() => active && setError("Your training plan could not be loaded. Please try again."));
    return () => { active = false; };
  }, []);

  if (!data && !error) return <LoadingState />;
  if (error) return <main className="mx-auto max-w-3xl p-6"><div role="alert" className="panel border-red-200 text-red-700 dark:border-red-900 dark:text-red-300">{error}</div></main>;

  const week = data.current_week;
  const next = data.next_activity;
  const actionRoute = next?.destination_route || (week ? `/training/week/${week.week_number}` : "/training/content");
  const actionLabel = data.training_complete
    ? "Review Training"
    : week?.required_complete === 0
      ? (week.week_number === 0 ? "Start Training" : `Begin Week ${week.week_number}`)
      : "Continue Training";

  const weeks = data.weeks || [];
  const currentIndex = weeks.findIndex((item) => item.week_number === week?.week_number);
  const upNext = currentIndex >= 0 ? weeks.slice(currentIndex + 1).find((item) => item) : null;
  const recentlyCompleted = weeks.filter((item) => item.is_complete).slice(-3).reverse();

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-950 dark:text-white">Learning Path</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">Where you are right now — and what comes next.</p>
      </div>
      <TrainingSubnav />

      {week ? (
        <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 p-5 text-white shadow-lg sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-100">{data.training_complete ? "Training Complete" : "Current"}</p>
          <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{week.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-blue-100">{week.description}</p>
          <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex justify-between text-sm"><span>{week.required_complete} of {week.required_total} required activities complete</span><strong>{week.completion_percent}%</strong></div>
              <div className="h-3 overflow-hidden rounded-full bg-blue-950/40"><div className="h-full rounded-full bg-white transition-all" style={{ width: `${week.completion_percent}%` }} /></div>
              {next ? <p className="mt-3 truncate text-sm text-blue-100">Next: {next.activity_label} — {next.title}</p> : null}
            </div>
            <Link to={actionRoute} className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-blue-700 shadow hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">{actionLabel}<ArrowRight size={18} /></Link>
          </div>
        </section>
      ) : <section className="panel"><h2 className="text-xl font-semibold">No active training weeks</h2><p className="mt-2 text-slate-600 dark:text-slate-300">Ask an administrator to enable a training week.</p></section>}

      <section className="grid gap-4 md:grid-cols-2">
        {upNext ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Up Next</p>
            <h3 className="mt-1 font-bold text-slate-900 dark:text-white">{upNext.title}</h3>
            <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{upNext.description}</p>
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{upNext.locked ? (upNext.lock_reason || "Finish your current work to unlock this.") : "Unlocked — you can start this after your current work."}</p>
          </div>
        ) : null}
        {recentlyCompleted.length ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Recently Completed</p>
            <ul className="mt-2 space-y-2">
              {recentlyCompleted.map((item) => (
                <li key={item.id}>
                  <Link to={`/training/week/${item.week_number}`} className="flex items-center gap-2 rounded-lg px-1 py-1 text-sm font-medium text-slate-700 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-slate-300 dark:hover:text-blue-300">
                    <Check className="shrink-0 text-emerald-500" size={16} />
                    <span className="min-w-0 truncate">{item.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <summary className="cursor-pointer list-none px-4 py-3 font-semibold text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-white">
          <span className="inline-flex items-center gap-1.5"><ChevronRight className="transition-transform [details[open]_&]:rotate-90" size={16} aria-hidden="true" />View full learning path ({weeks.length} weeks)</span>
        </summary>
        <div className="border-t border-slate-200 p-4 dark:border-slate-700">
          <div className="grid gap-3 md:grid-cols-2">
            {weeks.map((item) => {
              const card = (
                <div className={`h-full rounded-xl border p-4 transition ${item.week_number === week?.week_number ? "border-blue-500 bg-blue-50 shadow-sm dark:border-blue-500 dark:bg-blue-950/20" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Week {item.week_number}</p><h3 className="mt-1 font-bold text-slate-900 dark:text-white">{item.title}</h3></div>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${item.locked ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" : item.is_complete ? "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300" : "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"}`}>{item.locked ? <Lock size={12} /> : item.is_complete ? <Check size={12} /> : null}{statusLabels[item.status]}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{item.description}</p>
                  <div className="mt-4 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400"><span>{item.required_complete} of {item.required_total} required</span>{item.required_estimated_minutes ? <span className="inline-flex items-center gap-1"><Clock size={13} />About {Math.ceil(item.required_estimated_minutes / 60)} hr</span> : null}</div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-full rounded-full bg-blue-600" style={{ width: `${item.completion_percent}%` }} /></div>
                  {item.lock_reason ? <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{item.lock_reason}</p> : null}
                </div>
              );
              return item.locked ? <div key={item.id}>{card}</div> : <Link key={item.id} to={`/training/week/${item.week_number}`} className="rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">{card}</Link>;
            })}
          </div>
        </div>
      </details>
    </main>
  );
}
