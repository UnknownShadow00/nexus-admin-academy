import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState";
import { getDashboard, getLeaderboard } from "../services/api";

export default function StudentHome() {
  const [dashboard, setDashboard] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);

  useEffect(() => {
    getDashboard(1).then((res) => setDashboard(res.data));
    getLeaderboard().then((res) => setLeaderboard(res.data || []));
  }, []);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <section className="panel bg-gradient-to-r from-sky-600 to-blue-700 text-white">
        <h1 className="text-3xl font-bold">Student Dashboard</h1>
        <p className="mt-2 text-sm text-blue-100">Hands-on Windows Server and Microsoft 365 training progression.</p>
      </section>

      {!dashboard ? (
        <EmptyState icon="??" title="Loading dashboard" message="Fetching your latest progress..." />
      ) : (
        <section className="grid gap-4 md:grid-cols-3">
          <article className="panel dark:bg-slate-900 dark:border-slate-700"><p className="text-sm text-slate-500">Student</p><p className="text-2xl font-bold">{dashboard.student.name}</p></article>
          <article className="panel dark:bg-slate-900 dark:border-slate-700"><p className="text-sm text-slate-500">Total XP</p><p className="text-2xl font-bold">{dashboard.student.total_xp}</p></article>
          <article className="panel dark:bg-slate-900 dark:border-slate-700"><p className="text-sm text-slate-500">Level</p><p className="text-2xl font-bold">{dashboard.student.level_name}</p></article>
        </section>
      )}

      <section className="panel dark:bg-slate-900 dark:border-slate-700">
        <h2 className="text-xl font-semibold">Leaderboard</h2>
        <div className="mt-3 space-y-2">
          {leaderboard.map((entry) => (
            <div key={entry.student_id} className="flex items-center justify-between rounded border border-slate-200 p-2 dark:border-slate-700">
              <span>#{entry.rank} {entry.name}</span>
              <span>{entry.total_xp} XP</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
