import { Check, ChevronLeft, Clock, ExternalLink, Lock } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import TrainingSubnav from "../components/TrainingSubnav";
import { getTrainingWeek, markTrainingVideoWatched } from "../services/api";

const learnTypes = new Set(["lesson", "video", "quiz"]);

function ActivityCard({ activity, onWatched, returnTo }) {
  const quiz = activity.linked_quiz;
  const actionLabel = activity.complete ? "Review" : activity.status === "in_progress" ? "Continue" : "Start";
  return (
    <article id={activity.stable_id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 ${activity.complete ? "border-green-500 bg-green-500 text-white" : activity.status === "locked" ? "border-slate-300 text-slate-400 dark:border-slate-600" : "border-blue-300 text-blue-600 dark:border-blue-700"}`}>{activity.complete ? <Check size={16} /> : activity.status === "locked" ? <Lock size={14} /> : ""}</span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400">{activity.activity_label}</span><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${activity.is_required ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" : "bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300"}`}>{activity.requirement_label}</span>{activity.estimated_minutes ? <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Clock size={12} />{activity.estimated_minutes} min</span> : null}</div>
            <h3 className="mt-1 font-bold text-slate-900 dark:text-white">{activity.title}</h3>
            {activity.description ? <p className="mt-1 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{activity.description}</p> : null}
            {activity.score_percent != null ? <p className="mt-2 text-sm font-semibold text-green-700 dark:text-green-300">Quiz score: {activity.score}/{activity.total} ({activity.score_percent}%)</p> : null}
            {!activity.prerequisite_met ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">Recommended first: {activity.prerequisite_title}</p> : null}
            {activity.permission_reason ? <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">{activity.permission_reason}</p> : null}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 sm:max-w-xs sm:justify-end">
          {activity.activity_type === "video" && activity.external_url ? <a href={activity.external_url} target="_blank" rel="noreferrer" className="btn-secondary min-h-10">{activity.complete ? "Watch Again" : "Watch Video"}<ExternalLink size={14} /></a> : null}
          {activity.activity_type === "video" && !activity.complete ? <button type="button" onClick={() => onWatched(activity)} className="btn-secondary min-h-10">Mark Watched</button> : null}
          {quiz?.available ? <Link className="btn-secondary min-h-10" to={quiz.action === "review" ? quiz.review_route : quiz.route} state={{ returnTo }}>{quiz.action === "review" ? `Review Quiz${quiz.score_percent != null ? ` · ${quiz.score_percent}%` : ""}` : "Take Quiz"}</Link> : null}
          {!quiz?.available && quiz?.label ? <span className="inline-flex min-h-10 items-center text-xs text-slate-500">{quiz.label}</span> : null}
          {activity.activity_type !== "video" && activity.destination_route ? <Link className="btn-primary min-h-10" to={activity.destination_route} state={activity.activity_type === "quiz" ? { returnTo } : undefined}>{actionLabel}</Link> : null}
        </div>
      </div>
    </article>
  );
}

export default function TrainingWeekPage() {
  const { weekId } = useParams();
  const location = useLocation();
  const [week, setWeek] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => getTrainingWeek(weekId, { suppressToast: true }).then((res) => { setWeek(res.data); setError(""); }).catch((err) => setError(err?.response?.status === 403 ? "This week is locked. Complete the previous week first." : "This training week could not be loaded.")), [weekId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const activityId = new URLSearchParams(location.search).get("activity");
    if (week && activityId) requestAnimationFrame(() => document.getElementById(activityId)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }, [location.search, week]);
  const handleWatched = async (activity) => {
    await markTrainingVideoWatched(activity.id);
    await load();
  };
  if (error) return <main className="mx-auto max-w-3xl p-6"><Link className="mb-4 inline-flex items-center gap-1 text-blue-600" to="/training"><ChevronLeft size={16} />My Training</Link><div role="alert" className="panel">{error}</div></main>;
  if (!week) return <main className="mx-auto max-w-5xl p-6"><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;
  const learn = week.activities.filter((item) => learnTypes.has(item.activity_type));
  const practice = week.activities.filter((item) => !learnTypes.has(item.activity_type));
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
      <Link className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to="/training"><ChevronLeft size={16} />Weekly Plan</Link>
      <TrainingSubnav />
      <header className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 sm:p-7">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Week {week.week_number}</p><h1 className="mt-2 text-3xl font-bold text-slate-950 dark:text-white">{week.title}</h1><p className="mt-2 max-w-3xl text-slate-600 dark:text-slate-300">{week.description}</p>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end"><div><div className="mb-2 flex justify-between text-sm text-slate-600 dark:text-slate-300"><span>{week.required_complete} of {week.required_total} required complete</span><strong>{week.completion_percent}%</strong></div><div className="h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-full bg-blue-600" style={{ width: `${week.completion_percent}%` }} /></div></div>{week.next_activity?.destination_route ? <Link className="btn-primary" to={week.next_activity.destination_route}>Continue Next Activity</Link> : null}</div>
        {week.learning_goals?.length ? <div className="mt-5"><h2 className="font-bold text-slate-900 dark:text-white">Learning goals</h2><ul className="mt-2 grid gap-1 text-sm text-slate-600 dark:text-slate-300 sm:grid-cols-2">{week.learning_goals.map((goal) => <li key={goal} className="flex gap-2"><Check size={15} className="mt-0.5 shrink-0 text-blue-600" />{goal}</li>)}</ul></div> : null}
      </header>
      <section className="space-y-3"><div><h2 className="text-2xl font-bold text-slate-950 dark:text-white">Learn</h2><p className="text-sm text-slate-600 dark:text-slate-300">Learn each topic, then take its linked quiz when one is available.</p></div>{learn.length ? learn.map((item) => <ActivityCard key={item.id} activity={item} onWatched={handleWatched} returnTo={`/training/week/${week.week_number}`} />) : <p className="panel text-sm text-slate-500">No learning activities are assigned.</p>}</section>
      <section className="space-y-3"><div><h2 className="text-2xl font-bold text-slate-950 dark:text-white">Practice</h2><p className="text-sm text-slate-600 dark:text-slate-300">Apply this week’s skills. Optional work never blocks the next week.</p></div>{practice.length ? practice.map((item) => <ActivityCard key={item.id} activity={item} onWatched={handleWatched} returnTo={`/training/week/${week.week_number}`} />) : <p className="panel text-sm text-slate-500">No practical activity is currently mapped to this week.</p>}</section>
      <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-900 dark:bg-blue-950/20"><h2 className="text-xl font-bold text-slate-950 dark:text-white">{week.is_complete ? `Week ${week.week_number} Complete` : `Week ${week.week_number} Progress`}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{week.required_complete} of {week.required_total} required activities complete</p>{week.next_activity?.destination_route ? <Link className="btn-primary mt-4" to={week.next_activity.destination_route}>Continue Next Activity</Link> : <Link className="btn-primary mt-4" to="/training">Return to Weekly Plan</Link>}</section>
    </main>
  );
}
