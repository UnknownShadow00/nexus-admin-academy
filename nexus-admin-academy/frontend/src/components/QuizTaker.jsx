import { useEffect, useMemo, useState } from "react";
import { Spinner } from "./icons";
import { getQuiz, submitQuiz } from "../services/api";

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getQuiz(quizId).then((res) => setQuiz(res.data));
  }, [quizId]);

  const answeredCount = useMemo(() => Object.keys(answers).length, [answers]);

  const onSubmit = async () => {
    if (answeredCount !== quiz.questions.length) {
      setError("Please answer all questions before submitting.");
      return;
    }

    setError("");
    setLoading(true);
    const payload = { student_id: studentId, answers };
    const res = await submitQuiz(quizId, payload);
    setResult(res.data);
    setLoading(false);
  };

  if (!quiz) return <div className="panel text-sm text-slate-500">Loading quiz...</div>;

  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <div className="panel">
        <h1 className="text-2xl font-bold text-gray-900">{quiz.title}</h1>
        <p className="mt-2 text-sm text-slate-600">Question progress: {answeredCount} of {quiz.questions.length}</p>
      </div>

      {quiz.questions.map((q, index) => (
        <article key={q.id} className="panel">
          <p className="mb-3 text-sm font-semibold text-blue-700">Question {index + 1} of {quiz.questions.length}</p>
          <h2 className="text-lg font-semibold text-gray-900">{q.question_text}</h2>
          <div className="mt-4 grid gap-2">
            {[
              ["A", q.option_a],
              ["B", q.option_b],
              ["C", q.option_c],
              ["D", q.option_d],
            ].map(([opt, label]) => {
              const selected = answers[q.id] === opt;
              return (
                <label
                  key={opt}
                  className={`cursor-pointer rounded-lg border p-3 text-sm shadow-sm transition-all duration-200 ${
                    selected ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name={`q_${q.id}`}
                    className="sr-only"
                    checked={selected}
                    onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                  />
                  <span className="font-semibold">{opt}.</span> {label}
                </label>
              );
            })}
          </div>
        </article>
      ))}

      {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <button className="btn-primary w-full" onClick={onSubmit} disabled={loading || answeredCount !== quiz.questions.length}>
        {loading ? <span className="inline-flex items-center gap-2"><Spinner className="h-4 w-4 animate-spin" /> Submitting...</span> : "Submit Quiz"}
      </button>

      {result && (
        <div className="panel space-y-2 border-emerald-200 bg-emerald-50">
          <p className="text-lg font-bold text-emerald-700">Score: {result.score}/{result.total} · XP: {result.xp_awarded}</p>
          {result.results?.map((r) => (
            <div key={r.question_id} className="rounded-lg border border-emerald-100 bg-white p-3 text-sm">
              <p className="font-semibold text-gray-900">Question {r.question_id}: {r.correct ? "Correct" : `Correct answer: ${r.correct_answer}`}</p>
              <p className="mt-1 text-slate-600">{r.explanation}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
