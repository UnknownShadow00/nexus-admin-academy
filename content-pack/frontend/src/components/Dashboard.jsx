import { Award, BookOpen, Ticket, Trophy } from "./icons";

export default function Dashboard({ dashboard }) {
  if (!dashboard) {
    return <section className="panel text-sm text-slate-500">Loading dashboard...</section>;
  }

  const totalXp = dashboard.student.total_xp || 0;
  const level = dashboard.student.level || 1;
  const xpToNext = 1000;
  const progress = Math.min((totalXp % xpToNext) / xpToNext, 1) * 100;

  const ticketsCompleted = dashboard.recent_activity?.filter((item) => item.type === "ticket").length || 0;
  const quizzesPassed = dashboard.recent_activity?.filter((item) => item.type === "quiz" && item.score >= 7).length || 0;

  const stats = [
    { label: "Total XP", value: totalXp, Icon: Award, color: "text-emerald-600" },
    { label: "Tickets Completed", value: ticketsCompleted, Icon: Ticket, color: "text-blue-600" },
    { label: "Quizzes Passed", value: quizzesPassed, Icon: BookOpen, color: "text-amber-600" },
  ];

  return (
    <section className="panel space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Student Progress</h2>
          <p className="text-sm text-slate-500">{dashboard.student.level_name} · Level {level}</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Level {level} badge</span>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-600">XP progress</span>
          <span className="font-semibold text-blue-700">{Math.round(progress)}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-100">
          <div className="xp-fill h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {stats.map(({ label, value, Icon, color }) => (
          <article key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
            <p className="mt-2 text-xl font-bold text-gray-900">{value}</p>
          </article>
        ))}
      </div>

      <div>
        <h3 className="mb-2 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <Trophy className="h-4 w-4 text-amber-500" /> Recent Activity
        </h3>
        <div className="space-y-2">
          {dashboard.recent_activity?.map((activity, idx) => (
            <div key={`${activity.type}-${idx}`} className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
              <p className="font-semibold text-gray-900">{activity.title}</p>
              <p className="text-slate-600">
                {activity.type.toUpperCase()} · Score {activity.score} · +{activity.xp} XP
              </p>
            </div>
          ))}
          {!dashboard.recent_activity?.length && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">No recent submissions yet.</p>}
        </div>
      </div>
    </section>
  );
}
