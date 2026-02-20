import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import EmptyState from "../components/EmptyState";
import { checkInStudent, getStudentStats } from "../services/api";
import { getSelectedProfile } from "../services/profile";

function SkeletonCard() {
  return (
    <div className="panel animate-pulse dark:border-slate-700 dark:bg-slate-900">
      <div className="h-5 w-2/3 rounded bg-slate-200 dark:bg-slate-700" />
      <div className="mt-3 h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
      <div className="mt-2 h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="mt-4 h-9 w-full rounded bg-slate-200 dark:bg-slate-700" />
    </div>
  );
}

export default function StudentHome() {
  const profile = getSelectedProfile();
  const studentId = profile?.id;
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!studentId) {
      setStats(null);
      return;
    }
    const run = async () => {
      await checkInStudent(studentId);
      const res = await getStudentStats(studentId);
      setStats(res?.data || null);
    };
    run();
  }, [studentId]);

  const continueTarget = useMemo(() => {
    if (!stats) return { label: "Continue", to: "/learning-path", detail: "Open your learning path" };
    if (stats.quizzes_completed < stats.total_quizzes) {
      return { label: "Continue Quiz Track", to: "/quizzes", detail: "You still have unpassed quizzes." };
    }
    if (stats.tickets_completed < stats.total_tickets) {
      return { label: "Continue Ticket Track", to: "/tickets", detail: "You have open ticket work to complete." };
    }
    return { label: "Review Learning Path", to: "/learning-path", detail: "All core items are complete. Review and reinforce." };
  }, [stats]);

  if (!studentId) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <EmptyState icon="USER" title="Select a profile" message="Choose your student profile to continue." />
        <Link className="btn-primary mt-4 inline-block" to="/select-profile">
          Select Profile
        </Link>
      </main>
    );
  }

  if (!stats) {
    return (
      <main className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </main>
    );
  }

  const recent = stats.recent_activity || [];
  const feedbackItem = recent.find((x) => x.type === "ticket");

  return (
    <main className="mx-auto max-w-5xl space-y-4 p-6">
      <section className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white">
        <h1 className="text-3xl font-bold">Welcome back, {stats.name}</h1>
        <p className="mt-1 text-blue-100">Hands-on Windows Server and Microsoft 365 training progression</p>
      </section>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-3xl font-bold text-blue-600">{stats.total_xp}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Total XP</p>
        </div>
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-4 text-center dark:border-orange-900 dark:bg-orange-950/20">
          <p className="text-3xl font-bold text-orange-500">{stats.streak || 0} 🔥</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Day Streak</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-3xl font-bold text-green-600">{stats.quizzes_completed || 0}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Quizzes Done</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-3xl font-bold text-purple-600">{stats.tickets_completed || 0}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Tickets Passed</p>
        </div>
      </div>

      <section className="rounded-xl border-2 border-blue-500 bg-blue-50 p-6 dark:border-blue-700 dark:bg-blue-950/20">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">Up Next</p>
        <h2 className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">{continueTarget.detail}</h2>
        <Link className="btn-primary mt-4 inline-block" to={continueTarget.to}>
          {continueTarget.label} →
        </Link>
      </section>

      {feedbackItem ? (
        <section className="rounded border border-blue-300 bg-blue-50 p-4 dark:border-blue-700 dark:bg-blue-950/20">
          <p className="font-semibold text-blue-900 dark:text-blue-300">New feedback available</p>
          <p className="text-sm text-blue-800 dark:text-blue-200">Your latest ticket has an update.</p>
          <Link className="mt-2 inline-block text-sm font-medium text-blue-700 underline dark:text-blue-300" to="/tickets">
            View feedback
          </Link>
        </section>
      ) : null}

      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-3 text-xl font-bold">Recent Activity</h2>
        <div className="space-y-2">
          {recent.slice(0, 5).map((item, i) => (
            <div key={`${item.type}-${i}`} className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
              <p className="font-medium">{item.title || item.description || "Activity"}</p>
              <p className="text-slate-500 dark:text-slate-400">{item.type === "quiz" ? "You passed a quiz" : "You submitted or updated a ticket"}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
