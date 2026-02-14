import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import Spinner from "./Spinner";
import { getQuiz, submitQuiz } from "../services/api";

function progressKey(quizId) {
  return `quiz_${quizId}_progress`;
}

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const run = async () => {
      const res = await getQuiz(quizId);
      setQuiz(res.data);
      const existing = JSON.parse(localStorage.getItem(progressKey(quizId)) || "null");
      if (existing?.answers) setAnswers(existing.answers);
      setLoading(false);
    };
    run();
  }, [quizId]);

  const selectAnswer = (questionId, option) => {
    const next = { ...answers, [questionId]: option };
    setAnswers(next);
    localStorage.setItem(progressKey(quizId), JSON.stringify({ answers: next, submitted: false }));
  };

  const onSubmit = async () => {
    const loadingToast = toast.loading("Submitting quiz...");
    const res = await submitQuiz(quizId, { student_id: studentId, answers });
    toast.dismiss(loadingToast);
    toast.success(res.data?.is_first_attempt ? `Quiz completed! +${res.data?.xp_awarded} XP earned` : "Score updated (no XP for retakes)");
    setResult(res.data);
    localStorage.removeItem(progressKey(quizId));
  };

  if (loading) return <div className="panel"><Spinner text="Loading questions..." /></div>;

  return (
    <section className="space-y-4">
      <article className="panel dark:bg-slate-900 dark:border-slate-700">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{quiz.title}</h2>
      </article>

      {quiz.questions.map((q, idx) => (
        <article key={q.id} className="panel dark:bg-slate-900 dark:border-slate-700">
          <p className="mb-2 font-semibold text-slate-900 dark:text-slate-100">Q{idx + 1}. {q.question_text}</p>
          {["A", "B", "C", "D"].map((opt) => (
            <label key={opt} className="mb-1 block rounded border border-slate-200 p-2 dark:border-slate-700">
              <input type="radio" name={`q_${q.id}`} className="mr-2" checked={answers[q.id] === opt} onChange={() => selectAnswer(q.id, opt)} />
              {q[`option_${opt.toLowerCase()}`]}
            </label>
          ))}
        </article>
      ))}

      <button className="btn-primary" onClick={onSubmit}>Submit Quiz</button>

      {result ? (
        <article className="panel border-green-300 bg-green-50 dark:bg-green-950/20 dark:border-green-800">
          <p className="font-semibold">Score: {result.score}/{result.total}</p>
          <p>XP Awarded: {result.xp_awarded}</p>
          <p>{result.message}</p>
        </article>
      ) : null}
    </section>
  );
}
