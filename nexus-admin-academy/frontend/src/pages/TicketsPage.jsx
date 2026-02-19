import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import EmptyState from "../components/EmptyState";
import { getTickets } from "../services/api";
import { getSelectedProfile } from "../services/profile";

const difficultyClass = {
  1: "bg-emerald-100 text-emerald-700",
  2: "bg-lime-100 text-lime-700",
  3: "bg-amber-100 text-amber-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-red-100 text-red-700",
};

export default function TicketsPage() {
  const studentId = getSelectedProfile()?.id || 1;
  const [week, setWeek] = useState(1);
  const [status, setStatus] = useState("all");
  const [difficulty, setDifficulty] = useState("all");
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [methodologyBlocked, setMethodologyBlocked] = useState(false);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setMethodologyBlocked(false);
      try {
        const res = await getTickets(week, studentId);
        const tickets = Array.isArray(res.data) ? res.data : [];
        setItems(tickets);
      } catch (err) {
        if (err?.response?.status === 403) {
          setMethodologyBlocked(true);
        }
        setItems([]);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [week, studentId]);

  const filtered = useMemo(() => {
    if (!Array.isArray(items)) return [];
    return items.filter(
      (item) =>
        (status === "all" || item.status === status) &&
        (difficulty === "all" || Number(difficulty) === item.difficulty),
    );
  }, [items, status, difficulty]);

  if (methodologyBlocked) {
    return (
      <main className="mx-auto max-w-7xl p-6">
        <EmptyState
          icon="LOCK"
          title="Complete methodology training first"
          message="Finish your troubleshooting methodology training to unlock tickets."
        />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Available Tickets</h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            className="input-field max-w-24"
            type="number"
            min={1}
            value={week}
            onChange={(e) => setWeek(Number(e.target.value || 1))}
          />
          <select className="input-field max-w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All status</option>
            <option value="not_started">Not Started</option>
            <option value="pending">Awaiting Verification</option>
            <option value="in_review">In Review</option>
            <option value="passed">Passed</option>
            <option value="needs_revision">Needs Revision</option>
          </select>
          <select className="input-field max-w-40" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="all">Any difficulty</option>
            {[1, 2, 3, 4, 5].map((d) => (
              <option key={d} value={d}>{`Difficulty ${d}`}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="panel">
              <Skeleton height={22} />
              <Skeleton count={4} />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="NONE" title="No tickets assigned" message="New tickets will appear here each week" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((ticket) => (
            <article key={ticket.id} className="panel dark:bg-slate-900 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{ticket.title}</h3>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className={`rounded-full px-2 py-1 font-semibold ${difficultyClass[ticket.difficulty] || "bg-slate-100 text-slate-700"}`}>
                  Difficulty {ticket.difficulty}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Week {ticket.week_number}</span>
                <span className="rounded-full bg-blue-100 px-2 py-1 text-blue-700">{ticket.status.replace("_", " ")}</span>
              </div>
              {ticket.status === "passed" ? (
                <p className="mt-2 text-sm text-green-700 dark:text-green-300">
                  Score {ticket.score}/10 | XP {ticket.xp}
                </p>
              ) : null}
              <Link
                to={ticket.submission_id ? `/tickets/${ticket.submission_id}/feedback` : `/tickets/${ticket.id}`}
                className="btn-primary mt-3 w-full"
              >
                {ticket.submission_id ? "View Feedback" : "Start Ticket"}
              </Link>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
