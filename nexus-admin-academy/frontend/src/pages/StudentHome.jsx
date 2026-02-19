import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import { checkInStudent, getStudentStats } from "../services/api";
import { getSelectedProfile } from "../services/profile";

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
      setStats(res || null);
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
      <main className="mx-auto max-w-5xl p-6">
        <EmptyState icon="..." title="Loading" message="Fetching your latest progress..." />
      </main>
    );
  }

  const recent = stats.recent_activity || [];
  const feedbackItem = recent.find((x) => x.type === "ticket");

  return (
    <main className="mx-auto max-w-5xl space-y-4 p-6">
      <section className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white">
        <h1 className="text-3xl font-bold">Welcome back, {stats.name}</h1>
        <p className="mt-1 text-blue-100">XP Total: {stats.total_xp}</p>
      </section>

      <section className="rounded-lg bg-gradient-to-r from-orange-500 to-red-500 p-4 text-white">
        <p className="text-2xl font-bold">{stats.streak || 0} day streak</p>
      </section>

      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-xl font-bold">Continue</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{continueTarget.detail}</p>
        <Link className="btn-primary mt-3 inline-block" to={continueTarget.to}>
          {continueTarget.label}
        </Link>
      </section>

      {feedbackItem ? (
        <section className="rounded border border-blue-300 bg-blue-50 p-4">
          <p className="font-semibold text-blue-900">New feedback available</p>
          <p className="text-sm text-blue-800">Your latest ticket has an update.</p>
          <Link className="mt-2 inline-block text-sm font-medium text-blue-700 underline" to="/tickets">
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
              <p className="text-slate-500">{item.type === "quiz" ? "You passed a quiz" : "You submitted or updated a ticket"}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
