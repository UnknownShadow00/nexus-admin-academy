import { BookOpen, Brain, Flame, Ticket, Trophy, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FlashcardReviewPanel from "../components/FlashcardReviewPanel";
import { XPBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { getCurrentStudent } from "../hooks/useAuth";
import { checkInStudent, getStudentStats, getTrainingDashboard } from "../services/api";
import { iconSizes, scoreBand } from "../utils/theme";

function SkeletonCard() {
  return <div className="panel h-28 animate-pulse dark:border-slate-700 dark:bg-slate-900" />;
}

export default function StudentHome() {
  const studentId = getCurrentStudent()?.id;
  const [stats, setStats] = useState(null);
  const [training, setTraining] = useState(null);

  useEffect(() => {
    if (!studentId) return setStats(null);
    const run = async () => {
      try {
        await checkInStudent(studentId, { suppressToast: true });
        const [res, trainingRes] = await Promise.all([
          getStudentStats(studentId, { suppressToast: true }),
          getTrainingDashboard({ suppressToast: true }),
        ]);
        setStats(res?.data || null);
        setTraining(trainingRes?.data || null);
      } catch {
        setStats(null);
      }
    };
    run();
  }, [studentId]);

  const continueTarget = useMemo(() => {
    const week = training?.current_week;
    const next = training?.next_activity;
    if (!week) return { label: "Open My Training", to: "/training", title: "My Training", detail: "Open your weekly training plan." };
    if (training.training_complete) return { label: "Review Training", to: "/training", title: "Training Complete", detail: "Review completed weeks or revisit course content." };
    const fresh = week.week_number === 0 && week.required_complete === 0;
    return {
      label: fresh ? "Start Training" : "Continue Training",
      to: next?.destination_route || `/training/week/${week.week_number}`,
      title: fresh ? "Begin Your IT Training" : "Continue Your Training",
      detail: `Week ${week.week_number} — ${week.title}`,
    };
  }, [training]);

  if (!stats) {
    return (
      <main className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <SkeletonCard key={item} />)}
        </div>
      </main>
    );
  }

  const recent = (stats.recent_activity || []).slice(0, 5);
  const statCards = [
    { label: "Total XP", value: stats.total_xp || 0, to: "/learning-path", Icon: Zap, accent: "text-blue-600 dark:text-blue-400", card: "sm:col-span-2 lg:col-span-1" },
    { label: "Day Streak", value: stats.streak || 0, to: "/progress", Icon: Flame, accent: "text-orange-500 dark:text-orange-300" },
    { label: "Quizzes Done", value: stats.quizzes_completed || 0, to: "/quizzes", Icon: Trophy, accent: "text-emerald-600 dark:text-emerald-400" },
    { label: "Tickets Passed", value: stats.tickets_completed || 0, to: "/tickets", Icon: Ticket, accent: "text-violet-600 dark:text-violet-400" },
  ];

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader title={stats.name || "Student Home"} subtitle="Stay on track with your next lesson, quiz, and support ticket milestone." />

      <section className="rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 p-5 text-white shadow-lg sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">My Training</p>
        <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{continueTarget.title}</h2>
        <p className="mt-2 text-blue-100">{continueTarget.detail}</p>
        {training?.current_week ? <div className="mt-4 max-w-2xl"><div className="mb-1 flex justify-between text-sm"><span>{training.current_week.required_complete} of {training.current_week.required_total} required activities complete</span><strong>{training.current_week.completion_percent}%</strong></div><div className="h-2.5 overflow-hidden rounded-full bg-blue-950/40"><div className="h-full rounded-full bg-white" style={{ width: `${training.current_week.completion_percent}%` }} /></div></div> : null}
        <Link className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-white px-5 py-3 font-bold text-blue-700 hover:bg-blue-50" to={continueTarget.to}>{continueTarget.label}</Link>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map(({ label, value, to, Icon, accent, card }) => (
          <Link
            key={label}
            to={to}
            className={`panel group flex min-h-28 flex-col justify-between gap-4 p-4 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:hover:border-blue-700 ${card || ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
              </div>
              <span className={`rounded-xl bg-slate-100 p-2 dark:bg-slate-800 ${accent}`}>
                <Icon size={iconSizes.heading} aria-hidden="true" />
              </span>
            </div>
            <span className="text-sm font-medium text-blue-600 transition group-hover:text-blue-700 dark:text-blue-400 dark:group-hover:text-blue-300">Open {label.toLowerCase()}</span>
          </Link>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="rounded-lg bg-blue-100 p-2 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            <Brain size={iconSizes.heading} aria-hidden="true" />
          </span>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Daily Review</h2>
        </div>
        <div className="panel">
          <FlashcardReviewPanel />
        </div>
      </section>

      <section className="panel flex flex-col gap-4 border-slate-200 bg-slate-50/70 dark:border-slate-700 dark:bg-slate-900/70 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">Up Next</p>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{continueTarget.detail}</h2>
        </div>
        <Link className="btn-primary shrink-0" to={continueTarget.to}>{continueTarget.label}</Link>
      </section>

      <section className="panel space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Recent Activity</h2>
          <Link className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300" to="/progress">View progress</Link>
        </div>
        {recent.length ? recent.map((item, index) => {
          const Icon = item.type === "ticket" ? Ticket : BookOpen;
          const scorePct = item.score != null ? (item.score / 10) * 100 : null;
          return (
            <div key={`${item.type}-${index}`} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  <Icon size={iconSizes.inline} aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-900 dark:text-slate-100">{item.title || "Activity"}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Recent update"}</p>
                </div>
              </div>
              {item.score != null ? (
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${scoreBand.classes[scoreBand(scorePct)]}`}>Score {item.score}/10</span>
              ) : item.xp != null ? (
                <div className="shrink-0"><XPBadge amount={item.xp} /></div>
              ) : null}
            </div>
          );
        }) : <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">No recent submissions yet.</p>}
      </section>
    </main>
  );
}
