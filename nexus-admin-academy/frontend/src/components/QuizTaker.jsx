import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { getQuiz, submitQuiz } from "../services/api";
import Spinner from "./Spinner";

function progressKey(quizId) {
  return `quiz_${quizId}_progress`;
}

/** Fisher-Yates shuffle — returns a new array, never mutates */
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Build the display-order of questions and options.
 * On first attempt: stable original order.
 * On retake: both question order and each question's option order are shuffled.
 *
 * Each returned question gets:
 *   mappedOptions   — array of { displayLetter, realLetter, text } to render
 *   displayToReal   — { "B": "D", ... } maps display letter → real letter for scoring
 *   realToDisplay   — { "D": "B", ... } maps real letter → display letter for restoring saved answers
 */
function buildShuffledQuiz(questions, isRetake) {
  const ordered = isRetake ? shuffle(questions) : [...questions];

  return ordered.map((q) => {
    const realOptions = ["A", "B", "C", "D"]
      .map((letter) => ({ realLetter: letter, text: q[`option_${letter.toLowerCase()}`] }))
      .filter((o) => o.text);

    const displayOptions = isRetake ? shuffle(realOptions) : realOptions;

    const mappedOptions = displayOptions.map((o, i) => ({
      ...o,
      displayLetter: String.fromCharCode(65 + i),
    }));

    const displayToReal = {};
    const realToDisplay = {};
    mappedOptions.forEach((o) => {
      displayToReal[o.displayLetter] = o.realLetter;
      realToDisplay[o.realLetter] = o.displayLetter;
    });

    return { ...q, mappedOptions, displayToReal, realToDisplay };
  });
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
      <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
        isCorrect ? "border-green-600 bg-green-600 text-white"
        : isStudentWrong ? "border-red-500 bg-red-500 text-white"
        : "border-slate-300 text-slate-400 dark:border-slate-600"
      }`}>{letter}</span>
      <span className="flex-1">{text}</span>
      {isCorrect && studentAnswer === letter && <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400">✓ Correct</span>}
      {isCorrect && studentAnswer !== letter && <span className="ml-auto text-xs font-bold text-green-600 dark:text-green-400">✓ Correct answer</span>}
      {isStudentWrong && <span className="ml-auto text-xs font-bold text-red-600 dark:text-red-400">✗ Your answer</span>}
    </div>
  );
}

function ReviewScreen({ quiz, result, onRetake }) {
  const byId = {};
  (result.results || []).forEach((r) => { byId[r.question_id] = r; });
  const pct = Math.round((result.score / result.total) * 100);

  return (
    <div className="space-y-4">
      {/* Score hero */}
      <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
        <p className="text-7xl font-bold">
          {result.score}<span className="text-4xl text-blue-300">/{result.total}</span>
        </p>
        <p className="mt-2 text-2xl font-semibold">{pct}%</p>
        <p className="mt-2 text-blue-100">
          {result.xp_awarded > 0 ? `+${result.xp_awarded} XP earned` : "No XP for retakes"}
        </p>
      </div>

      {/* Stats */}
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

      {/* Answer review — always shows canonical A/B/C/D regardless of how they were displayed */}
      <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Answer Review</h3>
      {(quiz.questions || []).map((q, idx) => {
        const r = byId[q.id];
        const studentAnswer = r?.student_answer;
        const correctAnswers = r?.correct_answers || [r?.correct_answer || q.correct_answer];
        const isCorrect = r?.is_correct;
        const options = r?.options || { A: q.option_a, B: q.option_b, C: q.option_c, D: q.option_d };

        return (
          <div key={q.id} className={`rounded-xl border p-4 ${
            isCorrect ? "border-green-200 dark:border-green-900" : "border-red-200 dark:border-red-900"
          }`}>
            <div className="mb-3 flex items-start justify-between gap-2">
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                Q{idx + 1}. {q.question_text}
              </p>
              <span className={`shrink-0 text-lg font-bold ${isCorrect ? "text-green-600" : "text-red-500"}`}>
                {isCorrect ? "✓" : "✗"}
              </span>
            </div>
            <div className="space-y-1.5">
              {["A", "B", "C", "D"].map((opt) => {
                const text = options[opt];
                if (!text) return null;
                return <OptionRow key={opt} letter={opt} text={text} correctAnswers={correctAnswers} studentAnswer={studentAnswer} />;
              })}
            </div>
            {r?.explanation && (
              <p className="mt-2 rounded bg-slate-50 p-2 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                💡 {r.explanation}
              </p>
            )}
          </div>
        );
      })}

      <div className="flex gap-3">
        <button className="btn-secondary flex-1" onClick={onRetake}>Retake Quiz</button>
        <Link to="/quizzes" className="btn-primary flex-1 text-center">Back to Quizzes</Link>
      </div>
    </div>
  );
}

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [isRetake, setIsRetake] = useState(false);
  // answers stores REAL letters: { [question.id]: "C" }
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  // Increment to trigger re-shuffle on retake
  const [shuffleSeed, setShuffleSeed] = useState(0);

  useEffect(() => {
    getQuiz(quizId, studentId).then((res) => {
      const data = res.data;
      setQuiz(data);
      setIsRetake((data.attempts?.length || 0) > 0);
      const saved = JSON.parse(localStorage.getItem(progressKey(quizId)) || "null");
      if (saved?.answers) setAnswers(saved.answers);
      setLoading(false);
    });
  }, [quizId, studentId]);

  // Re-runs when quiz loads, when isRetake changes, or when shuffleSeed increments
  const shuffledQuestions = useMemo(() => {
    if (!quiz) return [];
    return buildShuffledQuiz(quiz.questions, isRetake);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quiz, isRetake, shuffleSeed]);

  const selectAnswer = (questionId, displayLetter, shuffledQ) => {
    const realLetter = shuffledQ.displayToReal[displayLetter];
    const next = { ...answers, [questionId]: realLetter };
    setAnswers(next);
    localStorage.setItem(progressKey(quizId), JSON.stringify({ answers: next }));
  };

  const onSubmit = async () => {
    const unanswered = shuffledQuestions.length - Object.keys(answers).length;
    if (unanswered > 0 && !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)) return;

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
      toast.error("Submit failed — try again");
    } finally {
      setSubmitting(false);
    }
  };

  const onRetake = () => {
    setResult(null);
    setAnswers({});
    setCurrentIndex(0);
    setIsRetake(true);
    setShuffleSeed((s) => s + 1); // triggers new shuffle
  };

  if (loading) return <div className="panel"><Spinner text="Loading..." /></div>;
  if (result) return <ReviewScreen quiz={quiz} result={result} onRetake={onRetake} />;

  const shuffledQ = shuffledQuestions[currentIndex];
  const total = shuffledQuestions.length;
  const progress = ((currentIndex + 1) / total) * 100;
  const storedRealAnswer = answers[shuffledQ.id];
  const selectedDisplayLetter = storedRealAnswer ? shuffledQ.realToDisplay[storedRealAnswer] : null;

  return (
    <section className="space-y-4">
      {/* Retake notice */}
      {isRetake && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
          🔀 Retake — questions and answers are in a new random order
        </div>
      )}

      {/* Progress bar */}
      <div>
        <div className="mb-1 flex justify-between text-sm text-slate-500">
          <span>Question {currentIndex + 1} of {total}</span>
          <span>{Object.keys(answers).length} answered</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700">
          <div className="h-2 rounded-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Question jump grid */}
      <div className="flex flex-wrap gap-1.5">
        {shuffledQuestions.map((q, i) => (
          <button
            key={q.id}
            onClick={() => setCurrentIndex(i)}
            className={`flex h-8 w-8 items-center justify-center rounded text-xs font-bold transition-all ${
              i === currentIndex
                ? "bg-blue-600 text-white"
                : answers[q.id]
                ? "border border-green-300 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "border border-slate-200 bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* Question card */}
      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <p className="mb-4 font-semibold text-slate-900 dark:text-slate-100">
          {currentIndex + 1}. {shuffledQ.question_text}
        </p>
        <div className="space-y-2">
          {shuffledQ.mappedOptions.map(({ displayLetter, text }) => {
            const selected = selectedDisplayLetter === displayLetter;
            return (
              <label
                key={displayLetter}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all ${
                  selected
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                    : "border-slate-200 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800/50"
                }`}
              >
                <input
                  type="radio"
                  className="sr-only"
                  name={`q_${shuffledQ.id}`}
                  checked={selected}
                  onChange={() => selectAnswer(shuffledQ.id, displayLetter, shuffledQ)}
                />
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${
                  selected ? "border-blue-500 bg-blue-600 text-white" : "border-slate-300 dark:border-slate-600"
                }`}>
                  {displayLetter}
                </span>
                <span className="text-sm text-slate-800 dark:text-slate-200">{text}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex gap-2">
        {currentIndex > 0 && (
          <button className="btn-secondary flex-1" onClick={() => setCurrentIndex((i) => i - 1)}>
            ← Previous
          </button>
        )}
        {currentIndex < total - 1 ? (
          <button className="btn-primary flex-1" onClick={() => setCurrentIndex((i) => i + 1)}>
            Next →
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
