import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";

import { getQuiz, submitQuiz } from "../services/api";
import Spinner from "./Spinner";

function progressKey(quizId) {
  return `quiz_${quizId}_progress`;
}

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

function ReviewScreen({ quiz, result, onRetake }) {
  const byId = {};
  (result.results || []).forEach((row) => {
    byId[row.question_id] = row;
  });
  const pct = Math.round((result.score / result.total) * 100);

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
        <p className="text-7xl font-bold">
          {result.score}
          <span className="text-4xl text-blue-300">/{result.total}</span>
        </p>
        <p className="mt-2 text-2xl font-semibold">{pct}%</p>
        <p className="mt-2 text-blue-100">{result.xp_awarded > 0 ? `+${result.xp_awarded} XP earned` : "No XP for retakes"}</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-green-600">{result.score}</p>
          <p className="text-xs text-slate-500">Correct</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-red-500">{result.total - result.score}</p>
          <p className="text-xs text-slate-500">Wrong</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-blue-600">{result.xp_awarded}</p>
          <p className="text-xs text-slate-500">XP</p>
        </div>
      </div>

      <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Answer Review</h3>
      {(quiz.questions || []).map((question, index) => {
        const review = byId[question.id];
        const studentAnswer = review?.student_answer;
        const correctAnswers = review?.correct_answers || [review?.correct_answer || question.correct_answer];
        const isCorrect = review?.is_correct;
        const options = review?.options || {
          A: question.option_a,
          B: question.option_b,
          C: question.option_c,
          D: question.option_d,
        };

        return (
          <div key={question.id} className={`rounded-xl border p-4 ${isCorrect ? "border-green-200 dark:border-green-900" : "border-red-200 dark:border-red-900"}`}>
            <div className="mb-3 flex items-start justify-between gap-2">
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                Q{index + 1}. {question.question_text}
              </p>
              <span className="shrink-0 text-lg">{isCorrect ? "OK" : "X"}</span>
            </div>
            <div className="space-y-1.5">
              {["A", "B", "C", "D"].map((opt) => {
                const text = options[opt];
                if (!text) return null;
                return <OptionRow key={opt} letter={opt} text={text} correctAnswers={correctAnswers} studentAnswer={studentAnswer} />;
              })}
            </div>
            {review?.explanation ? (
              <p className="mt-2 rounded bg-slate-50 p-2 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">Tip: {review.explanation}</p>
            ) : null}
          </div>
        );
      })}

      <div className="flex gap-3">
        <button className="btn-secondary flex-1" onClick={onRetake}>
          Retake Quiz
        </button>
        <Link to="/quizzes" className="btn-primary flex-1 text-center">
          Back to Quizzes
        </Link>
      </div>
    </div>
  );
}

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    getQuiz(quizId, studentId).then((res) => {
      setQuiz(res.data);
      const saved = JSON.parse(localStorage.getItem(progressKey(quizId)) || "null");
      if (saved?.answers) setAnswers(saved.answers);
      setLoading(false);
    });
  }, [quizId, studentId]);

  const selectAnswer = (questionId, option) => {
    const next = { ...answers, [questionId]: option };
    setAnswers(next);
    localStorage.setItem(progressKey(quizId), JSON.stringify({ answers: next }));
  };

  const onSubmit = async () => {
    const unanswered = (quiz?.questions?.length || 0) - Object.keys(answers).length;
    if (unanswered > 0 && !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)) {
      return;
    }

    setSubmitting(true);
    const toastId = toast.loading("Submitting...");
    try {
      const res = await submitQuiz(quizId, { student_id: studentId, answers });
      toast.dismiss(toastId);
      toast.success(res.data?.xp_awarded > 0 ? `+${res.data.xp_awarded} XP earned!` : "Quiz submitted");
      setResult(res.data);
      localStorage.removeItem(progressKey(quizId));
    } catch {
      toast.dismiss(toastId);
      toast.error("Submit failed - try again");
    } finally {
      setSubmitting(false);
    }
  };

  const onRetake = () => {
    setResult(null);
    setAnswers({});
    setCurrentIndex(0);
  };

  if (loading) return <div className="panel"><Spinner text="Loading..." /></div>;
  if (result) return <ReviewScreen quiz={quiz} result={result} onRetake={onRetake} />;

  const question = quiz.questions[currentIndex];
  const total = quiz.questions.length;
  const progress = ((currentIndex + 1) / total) * 100;

  return (
    <section className="space-y-4">
      <div>
        <div className="mb-1 flex justify-between text-sm text-slate-500">
          <span>Question {currentIndex + 1} of {total}</span>
          <span>{Object.keys(answers).length} answered</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700">
          <div className="h-2 rounded-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <p className="mb-4 font-semibold text-slate-900 dark:text-slate-100">
          {currentIndex + 1}. {question.question_text}
        </p>
        <div className="space-y-2">
          {["A", "B", "C", "D"].map((opt) => {
            const text = question[`option_${opt.toLowerCase()}`];
            if (!text) return null;
            const selected = answers[question.id] === opt;
            return (
              <label
                key={opt}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all ${
                  selected ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30" : "border-slate-200 hover:border-slate-300 dark:border-slate-700"
                }`}
              >
                <input type="radio" className="sr-only" name={`q_${question.id}`} checked={selected} onChange={() => selectAnswer(question.id, opt)} />
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${
                    selected ? "border-blue-500 bg-blue-600 text-white" : "border-slate-300 dark:border-slate-600"
                  }`}
                >
                  {opt}
                </span>
                <span className="text-sm text-slate-800 dark:text-slate-200">{text}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="flex gap-2">
        {currentIndex > 0 ? (
          <button className="btn-secondary flex-1" onClick={() => setCurrentIndex((idx) => idx - 1)}>
            Previous
          </button>
        ) : null}
        {currentIndex < total - 1 ? (
          <button className="btn-primary flex-1" onClick={() => setCurrentIndex((idx) => idx + 1)}>
            Next
          </button>
        ) : (
          <button className="btn-primary flex-1" onClick={onSubmit} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit Quiz"}
          </button>
        )}
      </div>
    </section>
  );
}
