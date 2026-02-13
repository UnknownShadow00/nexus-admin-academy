export default function Leaderboard({ data }) {
  return (
    <section className="panel">
      <h2 className="text-xl font-semibold">Leaderboard</h2>
      <div className="mt-3 space-y-2">
        {data?.leaderboard?.map((entry) => (
          <div key={entry.student_id} className="flex items-center justify-between rounded border p-2">
            <span>
              #{entry.rank} {entry.name}
            </span>
            <span>{entry.total_xp} XP</span>
          </div>
        ))}
      </div>
    </section>
  );
}
