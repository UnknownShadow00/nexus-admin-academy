export default function Dashboard({ dashboard }) {
  if (!dashboard) return null;
  return (
    <section className="panel">
      <h2 className="text-xl font-semibold">Student Dashboard</h2>
      <p className="mt-2">{dashboard.student.name}</p>
      <p>Total XP: {dashboard.student.total_xp}</p>
      <p>
        Level {dashboard.student.level}: {dashboard.student.level_name}
      </p>
    </section>
  );
}
