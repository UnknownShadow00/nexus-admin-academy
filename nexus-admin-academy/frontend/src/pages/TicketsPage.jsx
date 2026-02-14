import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import EmptyState from "../components/EmptyState";
import { getTickets } from "../services/api";

const difficultyClass = {
  1: "bg-emerald-100 text-emerald-700",
  2: "bg-lime-100 text-lime-700",
  3: "bg-amber-100 text-amber-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-red-100 text-red-700",
};

export default function TicketsPage() {
  const [week, setWeek] = useState(1);
  const [status, setStatus] = useState("all");
  const [difficulty, setDifficulty] = useState("all");
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      const res = await getTickets(week, 1);
      setItems(res.data || []);
      setLoading(false);
    };
    run();
  }, [week]);

  const filtered = useMemo(() => {
    return items.filter((item) => (status === "all" || item.status === status) && (difficulty === "all" || Number(difficulty) === item.difficulty));
  }, [items, status, difficulty]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Available Tickets</h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <input className="input-field max-w-24" type="number" min={1} value={week} onChange={(e) => setWeek(Number(e.target.value || 1))} />
          <select className="input-field max-w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All status</option>
            <option value="not_started">Not Started</option>
            <option value="submitted">Pending Grading</option>
            <option value="graded">Graded</option>
          </select>
          <select className="input-field max-w-40" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="all">Any difficulty</option>
            {[1,2,3,4,5].map((d) => <option key={d} value={d}>{`Difficulty ${d}`}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="panel"><Skeleton height={22} /><Skeleton count={4} /></div>)}</div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="??" title="No tickets assigned" message="New tickets will appear here each week" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((ticket) => (
            <article key={ticket.id} className="panel dark:bg-slate-900 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{ticket.title}</h3>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className={`rounded-full px-2 py-1 font-semibold ${difficultyClass[ticket.difficulty] || "bg-slate-100 text-slate-700"}`}>Difficulty {ticket.difficulty}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Week {ticket.week_number}</span>
                <span className="rounded-full bg-blue-100 px-2 py-1 text-blue-700">{ticket.status.replace("_", " ")}</span>
              </div>
              {ticket.status === "graded" ? (
                <p className="mt-2 text-sm text-green-700 dark:text-green-300">Score {ticket.score}/10 ? XP {ticket.xp}</p>
              ) : null}
              <Link
                to={ticket.status === "graded" && ticket.submission_id ? `/tickets/${ticket.submission_id}/feedback` : `/tickets/${ticket.id}`}
                className="btn-primary mt-3 w-full"
              >
                {ticket.status === "graded" ? "View Feedback" : "Start Ticket"}
              </Link>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
