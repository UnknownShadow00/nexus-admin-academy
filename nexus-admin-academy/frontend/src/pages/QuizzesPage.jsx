import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import EmptyState from "../components/EmptyState";
import { getQuizzes } from "../services/api";

export default function QuizzesPage() {
  const [week, setWeek] = useState(1);
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      const res = await getQuizzes(week, 1);
      setItems(res.data || []);
      setLoading(false);
    };
    run();
  }, [week]);

  const filtered = useMemo(() => {
    if (status === "all") return items;
    return items.filter((q) => q.status === status);
  }, [items, status]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Available Quizzes</h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <input className="input-field max-w-24" type="number" value={week} min={1} onChange={(e) => setWeek(Number(e.target.value || 1))} />
          <select className="input-field max-w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All status</option>
            <option value="not_started">Not Started</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="panel"><Skeleton height={22} /><Skeleton count={4} /></div>)}</div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="??" title="No quizzes available yet" message="Check back after your instructor creates content for this week" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((quiz) => (
            <article key={quiz.id} className={`panel ${quiz.status === "completed" ? "border-green-300" : "border-slate-200"} dark:bg-slate-900 dark:border-slate-700`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{quiz.title}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">Week {quiz.week_number} ? {quiz.question_count} questions</p>
              {quiz.status === "completed" ? (
                <div className="mt-2 text-sm text-green-700 dark:text-green-300">
                  <p>Best: {quiz.best_score}/10</p>
                  <p>First Attempt XP: {quiz.first_attempt_xp}</p>
                  <p className="text-xs">Retakes allowed (no extra XP).</p>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Not started</p>
              )}
              <Link className="btn-primary mt-3 w-full" to={`/quizzes/${quiz.id}`}>{quiz.status === "completed" ? "Retake Quiz" : "Take Quiz"}</Link>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
