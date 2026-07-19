import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";
import EmptyState from "../components/EmptyState";
import { StatusBadge } from "../components/ui/Badge";
import FilterBar from "../components/ui/FilterBar";
import PageHeader from "../components/ui/PageHeader";
import { getCurrentStudent } from "../hooks/useAuth";
import { getQuizzes } from "../services/api";

const PURPOSE_LABELS = {
  required: "Required",
  practice: "Optional",
  remediation: "Remediation",
  cumulative: "Cumulative Review",
  gate: "Promotion Gate",
  certification: "Certification Practice",
};

function QuizCard({ quiz }) {
  const label = PURPOSE_LABELS[quiz.quiz_purpose] || (quiz.is_required ? "Required" : "Optional");
  return (
    <article className={`panel ${quiz.status === "completed" ? "border-green-300" : "border-slate-200"} dark:border-slate-700 dark:bg-slate-900`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <BookOpen size={18} className="text-blue-600" />
        <h3 className="min-w-0 flex-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{quiz.title}</h3>
        <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">{label}</span>
        <StatusBadge status={quiz.status || "not_started"} />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">Week {quiz.week_number}{" · "}{quiz.question_count} questions</p>
      {quiz.status === "completed" ? (
        <p className="mt-2 text-sm text-green-700 dark:text-green-300">
          Best: {quiz.best_score || 0}/{quiz.question_count} ({Math.round(((quiz.best_score || 0) / Math.max(quiz.question_count || 1, 1)) * 100)}%)
        </p>
      ) : <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Not started</p>}
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {quiz.status === "completed" ? <Link className="btn-secondary flex-1 text-center" to={`/quizzes/${quiz.id}/review`}>Review</Link> : null}
        <Link className="btn-primary flex-1 text-center" to={`/quizzes/${quiz.id}`}>{quiz.status === "completed" ? "Retake" : "Take Quiz"}</Link>
      </div>
    </article>
  );
}

function QuizSection({ title, description, quizzes }) {
  if (!quizzes.length) return null;
  return (
    <section className="space-y-3" aria-label={title}>
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{title}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{quizzes.map((quiz) => <QuizCard key={quiz.id} quiz={quiz} />)}</div>
    </section>
  );
}

export default function QuizzesPage() {
  const studentId = getCurrentStudent()?.id;
  const [week, setWeek] = useState(1);
  const [allWeeks, setAllWeeks] = useState(false);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getQuizzes(undefined, studentId, { suppressToast: true })
      .then((res) => { if (!cancelled) setItems(res.data || []); })
      .catch((err) => { if (!cancelled) { setItems([]); setError(err?.userMessage || "Unable to load quizzes right now."); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [studentId]);

  const sections = useMemo(() => {
    const inScope = (quiz) => allWeeks || quiz.week_number === week;
    return {
      required: items.filter((q) => inScope(q) && q.is_required && !["cumulative", "gate"].includes(q.quiz_purpose)),
      practice: items.filter((q) => inScope(q) && q.quiz_purpose === "practice"),
      remediation: items.filter((q) => q.quiz_purpose === "remediation"),
      cumulative: items.filter((q) => inScope(q) && ["cumulative", "gate"].includes(q.quiz_purpose)),
      certification: items.filter((q) => q.quiz_purpose === "certification" && q.show_in_practice_library),
      history: items.filter((q) => q.status === "completed"),
    };
  }, [items, week, allWeeks]);

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-4 sm:p-6">
      <PageHeader title="Quizzes" />
      <FilterBar>
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">Week
          <input className="input-field max-w-24" type="number" min={0} max={24} value={week} disabled={allWeeks} onChange={(event) => setWeek(Number(event.target.value || 0))} />
        </label>
        <button type="button" className={`rounded-lg border px-3 py-2 text-sm font-medium ${allWeeks ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 dark:border-slate-700"}`} onClick={() => setAllWeeks((value) => !value)}>All Weeks</button>
      </FilterBar>

      {loading ? <div className="panel animate-pulse">Loading quiz sections…</div> : null}
      {!loading && error ? <EmptyState icon={<BookOpen size={40} />} title="Quizzes are unavailable" message={error} /> : null}
      {!loading && !error && !items.length ? <EmptyState icon={<BookOpen size={40} />} title="No quizzes yet" message="Your mentor has not published quiz content yet." /> : null}
      {!loading && !error ? <>
        <QuizSection title="Required This Week" description="These validated assessments count toward weekly completion." quizzes={sections.required} />
        <QuizSection title="Practice This Week" description="Optional topic practice; attempts do not block progression." quizzes={sections.practice} />
        <QuizSection title="Remediation" description="Shown only when assigned by a mentor or triggered by a missed required assessment." quizzes={sections.remediation} />
        <QuizSection title="Cumulative and Gate Assessments" description="Reviews and promotion gates apply only at their assigned checkpoint." quizzes={sections.cumulative} />
        <QuizSection title="Certification Practice Library" description="Optional certification preparation; these banks never block Nexus progression." quizzes={sections.certification} />
        <QuizSection title="Completed Quiz History" description="Review prior required and optional attempts." quizzes={sections.history} />
      </> : null}
    </main>
  );
}
