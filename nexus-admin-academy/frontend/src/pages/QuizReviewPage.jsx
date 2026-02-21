import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Spinner from "../components/Spinner";
import { getQuizReview } from "../services/api";
import { getSelectedProfile } from "../services/profile";

function OptionRow({ letter, text, correctAnswers, studentAnswer }) {
  const isCorrect = correctAnswers.includes(letter);
  const isStudentWrong = studentAnswer === letter && !isCorrect;

  let cls = "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm ";
  if (isCorrect) {
    cls += "border-green-400 bg-green-100 text-green-900 font-semibold dark:border-green-700 dark:bg-green-900/30 dark:text-green-200";
  } else if (isStudentWrong) {
    cls += "border-red-400 bg-red-100 text-red-900 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200";
  } else {
    cls += "border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400";
  }

  return (
    <div className={cls}>
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
          isCorrect ? "border-green-600 bg-green-600 text-white" : isStudentWrong ? "border-red-500 bg-red-500 text-white" : "border-slate-300 text-slate-400 dark:border-slate-600"
        }`}
      >
        {letter}
      </span>
      <span className="flex-1">{text}</span>
      {isCorrect && studentAnswer === letter ? <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400">Correct</span> : null}
      {isCorrect && studentAnswer !== letter ? <span className="ml-auto text-xs font-bold text-green-600 dark:text-green-400">Correct answer</span> : null}
      {isStudentWrong ? <span className="ml-auto text-xs font-bold text-red-600 dark:text-red-400">Your answer</span> : null}
    </div>
  );
}

export default function QuizReviewPage() {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const studentId = getSelectedProfile()?.id || 1;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getQuizReview(quizId, studentId)
      .then((res) => setData(res.data))
      .catch(() => setError("No attempt found. Take the quiz first."))
      .finally(() => setLoading(false));
  }, [quizId, studentId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <Spinner text="Loading review..." />
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <p className="text-slate-500 dark:text-slate-400">{error}</p>
        <Link to="/quizzes" className="mt-3 inline-block text-blue-600">
          Back to Quizzes
        </Link>
      </main>
    );
  }

  const { title, score, total, xp_awarded: xpAwarded, results, questions } = data;
  const pct = Math.round((score / total) * 100);
  const byId = {};
  (results || []).forEach((row) => {
    byId[row.question_id] = row;
  });

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <button onClick={() => navigate("/quizzes")} className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700">
        <ArrowLeft size={16} /> Back to Quizzes
      </button>

      <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
        <h1 className="mb-3 text-lg font-semibold text-blue-200">{title}</h1>
        <p className="text-7xl font-bold">
          {score}
          <span className="text-4xl text-blue-300">/{total}</span>
        </p>
        <p className="mt-2 text-2xl font-semibold">{pct}%</p>
        {xpAwarded > 0 ? <p className="mt-2 text-blue-100">+{xpAwarded} XP earned</p> : null}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-green-600">{score}</p>
          <p className="text-xs text-slate-500">Correct</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-red-500">{total - score}</p>
          <p className="text-xs text-slate-500">Wrong</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-blue-600">{pct}%</p>
          <p className="text-xs text-slate-500">Score</p>
        </div>
      </div>

      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Answer Review</h2>
      {(questions || []).map((question, index) => {
        const row = byId[question.id];
        const studentAnswer = row?.student_answer;
        const correctAnswers = row?.correct_answers || [row?.correct_answer || question.correct_answer];
        const isCorrect = row?.is_correct;
        const options = row?.options || {
          A: question.option_a,
          B: question.option_b,
          C: question.option_c,
          D: question.option_d,
        };

        return (
          <div
            key={question.id}
            className={`rounded-xl border p-5 ${
              isCorrect ? "border-green-200 dark:border-green-900" : studentAnswer ? "border-red-200 dark:border-red-900" : "border-slate-200 dark:border-slate-700"
            }`}
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                Q{index + 1}. {question.question_text}
              </p>
              <span className={`shrink-0 text-lg font-bold ${isCorrect ? "text-green-600" : studentAnswer ? "text-red-500" : "text-slate-400"}`}>
                {isCorrect ? "✓" : studentAnswer ? "✗" : "—"}
              </span>
            </div>
            <div className="space-y-2">
              {["A", "B", "C", "D"].map((opt) => {
                const text = options[opt] || question[`option_${opt.toLowerCase()}`];
                if (!text) return null;
                return <OptionRow key={opt} letter={opt} text={text} correctAnswers={correctAnswers} studentAnswer={studentAnswer} />;
              })}
            </div>
            {!studentAnswer ? <p className="mt-2 text-xs italic text-slate-400">Not answered</p> : null}
            {row?.explanation ? (
              <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">Tip: {row.explanation}</p>
            ) : null}
          </div>
        );
      })}

      <div className="flex gap-3">
        <Link to={`/quizzes/${quizId}`} className="btn-primary flex-1 text-center">
          Retake Quiz
        </Link>
        <Link to="/quizzes" className="btn-secondary flex-1 text-center">
          Back to Quizzes
        </Link>
      </div>
    </main>
  );
}
