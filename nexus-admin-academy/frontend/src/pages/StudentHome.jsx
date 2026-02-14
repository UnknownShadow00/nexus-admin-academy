import { useEffect, useMemo, useState } from "react";
import confetti from "canvas-confetti";
import toast from "react-hot-toast";
import { BookOpen, CheckCircle, Target, TrendingUp } from "lucide-react";
import EmptyState from "../components/EmptyState";
import { getLeaderboard, getStudentStats } from "../services/api";

function StatCard({ icon, label, value, subtitle }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 flex items-center gap-3">
        {icon}
        <span className="font-medium text-slate-600 dark:text-slate-300">{label}</span>
      </div>
      <div className="mb-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{value}</div>
      <div className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</div>
    </div>
  );
}

export default function StudentHome() {
  const studentId = 1;
  const [stats, setStats] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);

  useEffect(() => {
    const run = async () => {
      const [statsRes, lbRes] = await Promise.all([getStudentStats(studentId), getLeaderboard()]);
      const next = statsRes || null;

      const prevLevel = Number(localStorage.getItem("last_level") || "-1");
      if (next?.level != null && prevLevel >= 0 && next.level > prevLevel) {
        confetti({ particleCount: 120, spread: 75, origin: { y: 0.6 } });
        toast.success(`Level up! You are now ${next.level_name}`);
      }
      if (next?.level != null) {
        localStorage.setItem("last_level", String(next.level));
      }

      setStats(next);
      setLeaderboard(lbRes.data || []);
    };
    run();
  }, []);

  const activity = useMemo(() => stats?.recent_activity || [], [stats]);

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      {!stats ? (
        <EmptyState icon=".." title="Loading dashboard" message="Fetching your latest progress..." />
      ) : (
        <>
          <section className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-8 text-white">
            <h1 className="text-3xl font-bold">Welcome back, {stats.name}</h1>
            <p className="mt-2 text-blue-100">Hands-on Windows Server and Microsoft 365 training progression</p>
          </section>

          {stats.streak > 0 && (
            <section className="rounded-lg bg-gradient-to-r from-orange-500 to-red-500 p-4 text-white">
              <p className="text-2xl font-bold">{stats.streak} Day Streak</p>
              <p className="text-sm text-orange-100">Keep it going. Longest: {stats.longest_streak} days</p>
            </section>
          )}

          {stats.weak_areas?.length > 0 && (
            <section className="border-l-4 border-orange-500 bg-orange-50 p-4">
              <h3 className="mb-2 font-bold text-orange-900">Areas Needing Review</h3>
              {stats.weak_areas.map((area, i) => (
                <p key={`${area.topic}-${i}`} className="text-sm text-orange-800">
                  <strong>{area.topic}:</strong> {area.avg_score}/10 avg ({area.attempts} attempts)
                </p>
              ))}
            </section>
          )}

          <section className="grid grid-cols-1 gap-6 md:grid-cols-4">
            <StatCard icon={<TrendingUp className="text-blue-600" size={24} />} label="Total XP" value={stats.total_xp} subtitle={`Level: ${stats.level_name}`} />
            <StatCard icon={<BookOpen className="text-green-600" size={24} />} label="Quizzes" value={`${stats.quizzes_completed}/${stats.total_quizzes}`} subtitle={`Avg: ${stats.avg_quiz_score}/10`} />
            <StatCard icon={<CheckCircle className="text-purple-600" size={24} />} label="Tickets" value={`${stats.tickets_completed}/${stats.total_tickets}`} subtitle={`Avg: ${stats.avg_ticket_score}/10`} />
            <StatCard icon={<Target className="text-orange-600" size={24} />} label="Week Progress" value={`${stats.week_completion}%`} subtitle={`Week ${stats.current_week}`} />
          </section>

          {stats.cert_readiness && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-4 text-xl font-bold">CompTIA A+ Readiness</h3>
              <div className="mb-4">
                <div className="mb-2 flex justify-between">
                  <span>Overall Progress</span>
                  <span className="font-bold">{stats.cert_readiness.overall_readiness}%</span>
                </div>
                <div className="h-4 w-full rounded-full bg-slate-200">
                  <div className="h-4 rounded-full bg-green-600" style={{ width: `${stats.cert_readiness.overall_readiness}%` }} />
                </div>
              </div>
              <div className="space-y-1 text-sm">
                {stats.cert_readiness.by_domain?.map((d) => (
                  <div key={d.domain} className="flex justify-between">
                    <span>Domain {d.domain}</span>
                    <span className={d.readiness >= 70 ? "text-green-600" : "text-orange-600"}>{d.readiness}%</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {stats.cohort_comparison && (
            <section className="border-l-4 border-blue-500 bg-blue-50 p-4">
              <h4 className="mb-2 font-bold text-blue-900">Cohort Comparison</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span>Your XP:</span><span className="font-semibold">{stats.cohort_comparison.your_xp}</span></div>
                <div className="flex justify-between"><span>Cohort Average:</span><span>{stats.cohort_comparison.avg_xp}</span></div>
                <div className="flex justify-between"><span>Performance:</span><span className={stats.cohort_comparison.percentile > 0 ? "font-semibold text-green-600" : "text-orange-600"}>{stats.cohort_comparison.percentile > 0 ? "+" : ""}{stats.cohort_comparison.percentile}% vs average</span></div>
              </div>
            </section>
          )}

          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-4 text-xl font-bold">Recent Activity</h2>
            <div className="space-y-3">
              {activity.map((item, i) => (
                <div key={`${item.type}-${i}`} className="flex items-center justify-between rounded bg-slate-50 p-3 dark:bg-slate-800/60">
                  <div>
                    <span className="font-medium">{item.title}</span>
                    <span className="ml-3 text-sm text-slate-500">{item.type === "quiz" ? "Quiz" : "Ticket"}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-green-600">{item.score}/10 - +{item.xp} XP</div>
                    <div className="text-xs text-slate-500">{item.timestamp ? new Date(item.timestamp).toLocaleDateString() : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-4 text-xl font-bold">Leaderboard</h2>
            <div className="space-y-2">
              {leaderboard.map((entry) => (
                <div key={entry.student_id} className="flex items-center justify-between rounded border border-slate-200 p-2 dark:border-slate-700">
                  <span>#{entry.rank} {entry.name}</span>
                  <span>{entry.total_xp} XP</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
