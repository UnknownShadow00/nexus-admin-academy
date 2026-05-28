import { BookOpen, Brain, Flame, Ticket, Trophy, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FlashcardReviewPanel from "../components/FlashcardReviewPanel";
import { XPBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { getCurrentStudent } from "../hooks/useAuth";
import { checkInStudent, getStudentStats } from "../services/api";
import { iconSizes, scoreBand } from "../utils/theme";

function SkeletonCard() {
  return <div className="panel h-28 animate-pulse dark:border-slate-700 dark:bg-slate-900" />;
}

export default function StudentHome() {
  const studentId = getCurrentStudent()?.id;
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!studentId) return setStats(null);
    const run = async () => {
      try {
        await checkInStudent(studentId, { suppressToast: true });
        const res = await getStudentStats(studentId, { suppressToast: true });
        setStats(res?.data || null);
      } catch {
        setStats(null);
      }
    };
    run();
  }, [studentId]);

  const continueTarget = useMemo(() => {
    if (!stats) return { label: "Open learning path", to: "/learning-path", detail: "Pick up where you left off in your training plan." };
    if (stats.quizzes_completed < stats.total_quizzes) return { label: "Continue quizzes", to: "/quizzes", detail: "You still have quiz checkpoints ready to complete." };
    if (stats.tickets_completed < stats.total_tickets) return { label: "Continue tickets", to: "/tickets", detail: "Your ticket queue still has hands-on work waiting." };
    return { label: "Review learning path", to: "/learning-path", detail: "Core work is complete. Review the path and reinforce weak spots." };
  }, [stats]);

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
    { label: "Day Streak", value: stats.streak || 0, to: "/study-tracker", Icon: Flame, accent: "text-orange-500 dark:text-orange-300" },
    { label: "Quizzes Done", value: stats.quizzes_completed || 0, to: "/quizzes", Icon: Trophy, accent: "text-emerald-600 dark:text-emerald-400" },
    { label: "Tickets Passed", value: stats.tickets_completed || 0, to: "/tickets", Icon: Ticket, accent: "text-violet-600 dark:text-violet-400" },
  ];

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader title={stats.name || "Student Home"} subtitle="Stay on track with your next lesson, quiz, and support ticket milestone." />

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
          <Link className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300" to="/study-tracker">View tracker</Link>
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
