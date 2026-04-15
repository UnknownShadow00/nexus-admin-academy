import { Trophy } from "./icons";

const medalColors = {
  1: "bg-amber-100 text-amber-700",
  2: "bg-slate-200 text-slate-700",
  3: "bg-orange-100 text-orange-700",
};

export default function Leaderboard({ data, currentStudentId }) {
  const entries = data?.leaderboard || [];
  const maxXp = Math.max(...entries.map((entry) => entry.total_xp), 1);

  return (
    <section className="panel">
      <h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-900">
        <Trophy className="h-5 w-5 text-amber-500" /> Leaderboard
      </h2>
      <div className="space-y-2">
        {entries.map((entry) => (
          <div
            key={entry.student_id}
            className={`rounded-lg border p-3 ${
              entry.student_id === currentStudentId ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-white"
            }`}
          >
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 font-semibold text-gray-900">
                <span className={`rounded-full px-2 py-0.5 text-xs ${medalColors[entry.rank] || "bg-slate-100 text-slate-600"}`}>#{entry.rank}</span>
                {entry.name}
              </span>
              <span className="font-semibold text-slate-700">{entry.total_xp} XP</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-blue-500" style={{ width: `${(entry.total_xp / maxXp) * 100}%` }} />
            </div>
          </div>
        ))}
        {!entries.length && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">Leaderboard is empty.</p>}
      </div>
    </section>
  );
}
