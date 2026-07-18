import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";
import EmptyState from "../components/EmptyState";
import { StatusBadge } from "../components/ui/Badge";
import FilterBar from "../components/ui/FilterBar";
import PageHeader from "../components/ui/PageHeader";
import WeekAccordion from "../components/ui/WeekAccordion";
import { getCurrentStudent } from "../hooks/useAuth";
import { getQuizzes } from "../services/api";

export default function QuizzesPage() {
  const studentId = getCurrentStudent()?.id;
  const [week, setWeek] = useState(1);
  const [allWeeks, setAllWeeks] = useState(false);
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await getQuizzes(allWeeks ? undefined : week, studentId, { suppressToast: true });
        if (!cancelled) setItems(res.data || []);
      } catch (err) {
        if (!cancelled) {
          setItems([]);
          setError(err?.userMessage || "Unable to load quizzes right now.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [week, allWeeks, studentId]);

  const filtered = useMemo(() => {
    if (status === "all") return items;
    return items.filter((q) => q.status === status);
  }, [items, status]);

  const renderQuiz = (quiz) => (
    <article key={quiz.id} className={`panel ${quiz.status === "completed" ? "border-green-300" : "border-slate-200"} dark:border-slate-700 dark:bg-slate-900`}>
      <div className="mb-2 flex items-center gap-2">
        <BookOpen size={18} className="text-blue-600" />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{quiz.title}</h3>
        <StatusBadge status={quiz.status || "not_started"} />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">Week {quiz.week_number}{" \u00b7 "}{quiz.video_count || 1} video(s){" \u00b7 "}{quiz.question_count} questions</p>
      {quiz.status === "completed" ? (
        <div className="mt-2 text-sm text-green-700 dark:text-green-300">
          <p>Completed{" \u00b7 "}Best: {quiz.best_score || 0}/{quiz.question_count} ({Math.round(((quiz.best_score || 0) / (quiz.question_count || 10)) * 100)}%)</p>
          <p>First Attempt XP: {quiz.first_attempt_xp}</p>
          <p className="text-xs">Retakes allowed (no extra XP).</p>
        </div>
      ) : (
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Not started</p>
      )}
      <div className="mt-3 space-y-2">
        {quiz.status === "completed" ? (
          <Link className="btn-secondary block w-full text-center" to={`/quizzes/${quiz.id}/review`}>
            Review Last Attempt
          </Link>
        ) : null}
        <Link className="btn-primary block w-full text-center" to={`/quizzes/${quiz.id}`}>
          {quiz.status === "completed" ? "Retake Quiz" : "Take Quiz"}
        </Link>
      </div>
    </article>
  );

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <PageHeader title="Quizzes" />
      <FilterBar>
        <label className="flex items-center gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Week:
          <input
            className="input-field max-w-24 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500"
            type="number"
            value={week}
            min={1}
            disabled={allWeeks}
            onChange={(e) => setWeek(Number(e.target.value || 1))}
          />
        </label>
        <button
          type="button"
          className={`rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700 ${
            allWeeks
              ? "bg-blue-600 text-white"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
          onClick={() => setAllWeeks((current) => !current)}
        >
          All Weeks
        </button>
        <select className="input-field max-w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All status</option>
          <option value="not_started">Not Started</option>
          <option value="completed">Completed</option>
        </select>
      </FilterBar>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="panel">
              <div className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-4 mb-2" />
              <div className="animate-pulse bg-slate-100 dark:bg-slate-800 rounded h-16" />
            </div>
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={<BookOpen size={40} className="text-slate-300" />} title="Quizzes are unavailable" message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={40} className="text-slate-300" />}
          title="No quizzes yet"
          message={allWeeks ? "Your instructor hasn't created any quizzes yet." : "Your instructor hasn't created quizzes for this week yet."}
        />
      ) : allWeeks ? (
        <WeekAccordion items={filtered} renderItem={renderQuiz} gridClassName="grid gap-4 md:grid-cols-2 xl:grid-cols-3" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map(renderQuiz)}
        </div>
      )}
    </main>
  );
}
