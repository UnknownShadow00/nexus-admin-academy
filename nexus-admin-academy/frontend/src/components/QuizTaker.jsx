import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { getQuiz, submitQuiz } from "../services/api";
import Spinner from "./Spinner";

function progressKey(quizId) {
  return `quiz_${quizId}_progress`;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString();
}

export default function QuizTaker({ quizId, studentId }) {
  const [phase, setPhase] = useState("loading");
  const [quiz, setQuiz] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [showAllReview, setShowAllReview] = useState(false);

  useEffect(() => {
    const run = async () => {
      setPhase("loading");
      const res = await getQuiz(quizId, studentId);
      const quizData = res.data;
      setQuiz(quizData);
      setAttempts(quizData.attempts || []);

      const existing = JSON.parse(localStorage.getItem(progressKey(quizId)) || "null");
      if (existing?.answers) {
        setAnswers(existing.answers);
      }
      if (typeof existing?.currentQuestion === "number") {
        setCurrentIndex(existing.currentQuestion);
      }

      setPhase("history");
    };
    run();
  }, [quizId, studentId]);

  const totalQuestions = quiz?.questions?.length || 0;
  const unansweredCount = useMemo(() => {
    if (!quiz?.questions) return 0;
    return quiz.questions.filter((question) => {
      const selected = answers[question.id] || answers[String(question.id)] || answers[String(question.question_number)];
      return !selected;
    }).length;
  }, [quiz, answers]);

  const percentComplete = totalQuestions > 0 ? Math.round(((currentIndex + 1) / totalQuestions) * 100) : 0;
  const currentQuestion = quiz?.questions?.[currentIndex];

  const selectAnswer = (questionId, option) => {
    const next = { ...answers, [questionId]: option };
    setAnswers(next);
    localStorage.setItem(progressKey(quizId), JSON.stringify({ answers: next, submitted: false, currentQuestion: currentIndex }));
  };

  const goNext = () => {
    setCurrentIndex((prev) => {
      const nextIndex = Math.min(prev + 1, totalQuestions - 1);
      localStorage.setItem(progressKey(quizId), JSON.stringify({ answers, submitted: false, currentQuestion: nextIndex }));
      return nextIndex;
    });
  };

  const goPrev = () => {
    setCurrentIndex((prev) => {
      const nextIndex = Math.max(prev - 1, 0);
      localStorage.setItem(progressKey(quizId), JSON.stringify({ answers, submitted: false, currentQuestion: nextIndex }));
      return nextIndex;
    });
  };

  const startQuiz = () => {
    setPhase("taking");
  };

  const onSubmit = async () => {
    if (unansweredCount > 0) {
      const confirmSubmit = window.confirm(`You have ${unansweredCount} unanswered question(s). Submit anyway?`);
      if (!confirmSubmit) return;
    }

    setPhase("submitting");
    try {
      const loadingToast = toast.loading("Submitting quiz...");
      const res = await submitQuiz(quizId, { student_id: studentId, answers });
      toast.dismiss(loadingToast);
      toast.success(res.data?.is_first_attempt ? `Quiz completed! +${res.data?.xp_awarded} XP earned` : "Score updated (no XP for retakes)");

      setResult(res.data);
      localStorage.removeItem(progressKey(quizId));
      setPhase("results");
    } catch (error) {
      setPhase("taking");
      throw error;
    }
  };

  if (phase === "loading") {
    return (
      <div className="panel">
        <Spinner text="Loading questions..." />
      </div>
    );
  }

  if (phase === "submitting") {
    return (
      <div className="panel">
        <Spinner text="Submitting quiz..." />
      </div>
    );
  }

  if (phase === "history") {
    const hasAttempts = attempts.length > 0;
    const bestScore = hasAttempts ? Math.max(...attempts.map((item) => item.score || 0)) : null;

    return (
      <section className="space-y-4">
        <article className="panel dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{quiz.title}</h2>
          <p className="mt-1 text-sm text-slate-500">{(quiz.source_urls || []).length} video(s) - {quiz.question_count || totalQuestions} questions</p>
        </article>

        {hasAttempts ? (
          <article className="panel dark:border-slate-700 dark:bg-slate-900">
            <h3 className="mb-3 text-lg font-semibold">Your attempts</h3>
            <div className="space-y-2">
              {attempts.map((attempt) => (
                <div key={`${attempt.attempt_number}-${attempt.created_at || "na"}`} className="flex items-center justify-between rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <span>
                    Attempt {attempt.attempt_number} - {Math.round(((attempt.score || 0) / (attempt.total || 1)) * 100)}% - {formatDate(attempt.created_at)}
                  </span>
                  <span className="text-slate-500">
                    {attempt.xp_awarded > 0 ? `+${attempt.xp_awarded} XP` : "No XP"}
                    {bestScore === attempt.score ? " - best" : ""}
                  </span>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        <button className="btn-primary" onClick={startQuiz}>Start Quiz</button>
      </section>
    );
  }

  if (phase === "results" && result) {
    const percent = Math.round(((result.score || 0) / (result.total || 1)) * 100);

    return (
      <section className="space-y-4">
        <div className="space-y-4">
          <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
            <p className="text-7xl font-bold">{result.score}<span className="text-4xl text-blue-300">/{result.total}</span></p>
            <p className="mt-2 text-2xl font-semibold">{percent}%</p>
            <p className="mt-2 text-blue-100">
              {result.xp_awarded > 0
                ? `+${result.xp_awarded} XP earned`
                : "No XP — score must improve to earn XP on retakes"}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
              <p className="text-2xl font-bold text-green-600">{result.score}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Correct</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
              <p className="text-2xl font-bold text-red-500">{result.total - result.score}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Wrong</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
              <p className="text-2xl font-bold text-blue-600">{result.xp_awarded}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">XP</p>
            </div>
          </div>
        </div>

        <article className="panel dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Answer Review</h3>
            <button className="btn-secondary" onClick={() => setShowAllReview((prev) => !prev)}>
              {showAllReview ? "Hide Details" : "Review All Questions"}
            </button>
          </div>

          <div className="space-y-3">
            {(result.results || []).map((item) => {
              const isWrong = !item.is_correct;
              const shouldShowDetails = showAllReview || isWrong;
              return (
                <div key={item.question_id} className={`rounded-lg border p-4 ${item.is_correct ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/20" : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30"}`}>
                  <div className="flex items-start justify-between gap-4">
                    <p className="font-medium">Q{item.question_number}. {item.question_text}</p>
                    <span className={item.is_correct ? "text-green-700 dark:text-green-400" : "text-red-700 dark:text-red-400"}>{item.is_correct ? "✓" : "✗"}</span>
                  </div>
                  {shouldShowDetails ? (
                    <div className="mt-2 space-y-1 text-sm">
                      <p>Your answer: {item.student_answer || "(no answer)"}</p>
                      <p>Correct answer: {item.correct_answer}</p>
                      <p className="text-sm text-slate-600 dark:text-slate-300">{item.explanation}</p>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </article>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <article className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{quiz.title}</h2>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-sm">
            <span>Question {currentIndex + 1} of {totalQuestions}</span>
            <span>{percentComplete}%</span>
          </div>
          <div className="h-2 w-full rounded bg-slate-200 dark:bg-slate-700">
            <div className="h-2 rounded bg-blue-600" style={{ width: `${percentComplete}%` }} />
          </div>
        </div>
      </article>

      {currentQuestion ? (
        <article className="panel dark:border-slate-700 dark:bg-slate-900">
          <p className="mb-2 font-semibold text-slate-900 dark:text-slate-100">
            Q{currentIndex + 1}. {currentQuestion.question_text}
          </p>
          {["A", "B", "C", "D"].map((opt) => (
            <label key={opt} className="mb-1 block rounded border border-slate-200 p-2 dark:border-slate-700">
              <input
                type="radio"
                name={`q_${currentQuestion.id}`}
                className="mr-2"
                checked={(answers[currentQuestion.id] || answers[String(currentQuestion.id)]) === opt}
                onChange={() => selectAnswer(currentQuestion.id, opt)}
              />
              {currentQuestion[`option_${opt.toLowerCase()}`]}
            </label>
          ))}
        </article>
      ) : null}

      <div className="flex items-center justify-between">
        <button className="btn-secondary" onClick={goPrev} disabled={currentIndex === 0}>Previous</button>
        {currentIndex < totalQuestions - 1 ? (
          <button className="btn-primary" onClick={goNext}>Next</button>
        ) : (
          <button className="btn-primary" onClick={onSubmit}>Submit Quiz</button>
        )}
      </div>
    </section>
  );
}
