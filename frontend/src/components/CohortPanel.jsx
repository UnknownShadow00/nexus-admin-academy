import { useEffect, useState } from "react";
import { getCohortSummary } from "../services/api";

function formatLastActive(value) {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";

  const elapsedMinutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));
  if (elapsedMinutes < 1) return "Just now";
  if (elapsedMinutes < 60) return `${elapsedMinutes}m ago`;
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours}h ago`;
  const elapsedDays = Math.floor(elapsedHours / 24);
  if (elapsedDays < 30) return `${elapsedDays}d ago`;
  return date.toLocaleDateString();
}

export default function CohortPanel() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getCohortSummary({ suppressToast: true })
      .then((response) => {
        if (!cancelled) setStudents(response?.data || []);
      })
      .catch(() => {
        if (!cancelled) setError("Cohort progress is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="panel dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Cohort Progress</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Required training completion and inactivity risk across all students.
        </p>
      </div>

      {loading ? <div className="h-28 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" /> : null}
      {!loading && error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
      {!loading && !error && !students.length ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No students are enrolled yet.</p>
      ) : null}
      {!loading && !error && students.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Current Week</th>
                <th className="min-w-44 px-2 py-2">% Complete</th>
                <th className="px-2 py-2">Last Active</th>
                <th className="px-2 py-2">At-Risk</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.student_id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                  <td className="px-2 py-2 font-medium text-slate-900 dark:text-slate-100">{student.name}</td>
                  <td className="px-2 py-2">
                    {student.current_week
                      ? `Week ${student.current_week.week_number} · ${student.current_week.status.replaceAll("_", " ")}`
                      : "No active week"}
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                        role="progressbar"
                        aria-label={`${student.name} training completion`}
                        aria-valuemin="0"
                        aria-valuemax="100"
                        aria-valuenow={student.overall_percent}
                      >
                        <div
                          className="h-full rounded-full bg-blue-600"
                          style={{ width: `${student.overall_percent}%` }}
                        />
                      </div>
                      <span className="w-10 text-right font-medium">{student.overall_percent}%</span>
                    </div>
                  </td>
                  <td className="px-2 py-2">{formatLastActive(student.last_active_at)}</td>
                  <td className="px-2 py-2">
                    <span
                      className={
                        student.is_at_risk
                          ? "rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-700 dark:bg-red-950/50 dark:text-red-300"
                          : "rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                      }
                    >
                      {student.is_at_risk ? "At risk" : "On track"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
