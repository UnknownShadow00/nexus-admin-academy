import { useEffect, useState } from "react";
import { getStudentsOverview } from "../services/api";

export default function AdminStudentsPage() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    getStudentsOverview().then((res) => setRows(res.data || []));
  }, []);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <h1 className="mb-4 text-2xl font-bold text-slate-900 dark:text-slate-100">Student Activity Overview</h1>
      <div className="panel overflow-x-auto dark:bg-slate-900 dark:border-slate-700">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-2 py-2">#</th>
              <th className="px-2 py-2">Name</th>
              <th className="px-2 py-2">XP</th>
              <th className="px-2 py-2">Quiz</th>
              <th className="px-2 py-2">Avg Quiz</th>
              <th className="px-2 py-2">Tickets</th>
              <th className="px-2 py-2">Avg Ticket</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.student_id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-2 py-2">{r.rank}</td>
                <td className="px-2 py-2">{r.name}</td>
                <td className="px-2 py-2">{r.xp}</td>
                <td className="px-2 py-2">{r.quiz_done}/{r.quiz_total}</td>
                <td className="px-2 py-2">{r.avg_quiz}</td>
                <td className="px-2 py-2">{r.ticket_done}/{r.ticket_total}</td>
                <td className="px-2 py-2">{r.avg_ticket}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
