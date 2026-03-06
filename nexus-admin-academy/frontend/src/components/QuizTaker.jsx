import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import { getQuiz, submitQuiz } from "../services/api";
import Spinner from "./Spinner";

const progressKey = (id) => `quiz_progress_${id}`;
const ALL_OPTS = ["A", "B", "C", "D", "E"];

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildShuffledQuestion(question) {
  // Build list of options that exist
  const rawOpts = ALL_OPTS
    .map((letter) => ({ letter, text: question[`option_${letter.toLowerCase()}`] }))
    .filter((o) => o.text);

  const shuffled = shuffle(rawOpts);

  // Map display letter (A/B/C/D/E) -> real letter
  const displayToReal = {};
  const realToDisplay = {};
  shuffled.forEach((opt, idx) => {
    const displayLetter = String.fromCharCode(65 + idx);
    displayToReal[displayLetter] = opt.letter;
    realToDisplay[opt.letter] = displayLetter;
  });

  return {
    ...question,
    shuffledOptions: shuffled.map((opt, idx) => ({
      display: String.fromCharCode(65 + idx),
      text: opt.text,
      realLetter: opt.letter,
    })),
    displayToReal,
    realToDisplay,
  };
}

function OptionRow({ letter, text, correctAnswers, studentAnswer }) {
  const studentAnswers = Array.isArray(studentAnswer)
    ? studentAnswer
    : studentAnswer
      ? [studentAnswer]
      : [];
  const isCorrect = correctAnswers.includes(letter);
  const isStudentPick = studentAnswers.includes(letter);
  const isWrong = isStudentPick && !isCorrect;

  let cls =
    "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-all ";
  if (isCorrect)
    cls +=
      "border-green-400 bg-green-100 text-green-900 font-semibold dark:border-green-700 dark:bg-green-900/30 dark:text-green-200";
  else if (isWrong)
    cls +=
      "border-red-400 bg-red-100 text-red-900 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200";
  else
    cls +=
      "border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400";

  return (
    <div className={cls}>
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
          isCorrect
            ? "border-green-600 bg-green-600 text-white dark:bg-green-500"
            : isWrong
              ? "border-red-500 bg-red-500 text-white"
              : "border-slate-300 text-slate-400 dark:border-slate-600"
        }`}
      >
        {letter}
      </span>
      <span className="flex-1">{text}</span>
      {isCorrect && isStudentPick && (
        <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400">
          Correct
        </span>
      )}
      {isCorrect && !isStudentPick && (
        <span className="ml-auto text-xs font-bold text-green-600 dark:text-green-400">
          Correct answer
        </span>
      )}
      {isWrong && (
        <span className="ml-auto text-xs font-bold text-red-600 dark:text-red-400">
          Your answer
        </span>
      )}
    </div>
  );
}

function ReviewScreen({ quiz, result, onRetake }) {
  const byId = {};
  (result.results || []).forEach((r) => {
    byId[r.question_id] = r;
  });

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
        <h2 className="mb-2 text-lg font-semibold text-blue-200">{quiz.title}</h2>
        <p className="text-7xl font-bold">
          {result.score}
          <span className="text-4xl text-blue-300">/{result.total}</span>
        </p>
        <p className="mt-2 text-2xl font-semibold">
          {Math.round((result.score / result.total) * 100)}%
        </p>
        {result.xp_awarded > 0 && (
          <p className="mt-2 text-blue-100">+{result.xp_awarded} XP earned!</p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-green-600">{result.score}</p>
          <p className="text-xs text-slate-500">Correct</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-red-500">{result.total - result.score}</p>
          <p className="text-xs text-slate-500">Wrong</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-blue-600">
            {Math.round((result.score / result.total) * 100)}%
          </p>
          <p className="text-xs text-slate-500">Score</p>
        </div>
      </div>

      <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
        Answer Review
      </h3>

      {(quiz.questions || []).map((question, index) => {
        const review = byId[question.id];
        const studentAnswer = review?.student_answer;
        const correctAnswers =
          review?.correct_answers || [review?.correct_answer || question.correct_answer];
        const isCorrect = review?.is_correct;
        const options = review?.options || {
          A: question.option_a,
          B: question.option_b,
          C: question.option_c,
          D: question.option_d,
          E: question.option_e || "",
        };

        // studentAnswer may be "A,C" for multi-select
        const studentAnswerArr = studentAnswer
          ? String(studentAnswer).split(",").map((s) => s.trim())
          : [];

        return (
          <div
            key={question.id}
            className={`rounded-xl border p-4 ${
              isCorrect
                ? "border-green-200 dark:border-green-900"
                : "border-red-200 dark:border-red-900"
            }`}
          >
            <div className="mb-3 flex items-start justify-between gap-2">
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                Q{index + 1}. {question.question_text}
              </p>
              <span className="shrink-0 text-lg">{isCorrect ? "?" : "?"}</span>
            </div>
            <div className="space-y-1.5">
              {ALL_OPTS.map((opt) => {
                const text = options[opt];
                if (!text) return null;
                return (
                  <OptionRow
                    key={opt}
                    letter={opt}
                    text={text}
                    correctAnswers={correctAnswers}
                    studentAnswer={studentAnswerArr}
                  />
                );
              })}
            </div>
            {review?.explanation ? (
              <p className="mt-2 rounded bg-slate-50 p-2 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {review.explanation}
              </p>
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
  const [shuffledQuestions, setShuffledQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    getQuiz(quizId, studentId).then((res) => {
      const q = res.data;
      setQuiz(q);
      const sq = shuffle(q.questions || []).map(buildShuffledQuestion);
      setShuffledQuestions(sq);
      const saved = JSON.parse(
        localStorage.getItem(progressKey(quizId)) || "null"
      );
      if (saved?.answers) setAnswers(saved.answers);
      setLoading(false);
    });
  }, [quizId, studentId]);

  const selectAnswer = (questionId, displayLetter, shuffledQ) => {
    const realLetter = shuffledQ.displayToReal[displayLetter];
    const isMulti = shuffledQ.is_multi_select;

    let next;
    if (isMulti) {
      const current = Array.isArray(answers[questionId])
        ? answers[questionId]
        : [];
      if (current.includes(realLetter)) {
        next = {
          ...answers,
          [questionId]: current.filter((l) => l !== realLetter),
        };
      } else {
        next = {
          ...answers,
          [questionId]: [...current, realLetter].sort(),
        };
      }
    } else {
      next = { ...answers, [questionId]: realLetter };
    }
    setAnswers(next);
    localStorage.setItem(
      progressKey(quizId),
      JSON.stringify({ answers: next })
    );
  };

  const onSubmit = async () => {
    const unanswered =
      (shuffledQuestions.length || 0) - Object.keys(answers).length;
    if (
      unanswered > 0 &&
      !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)
    )
      return;

    // Convert multi-select arrays to comma-separated strings
    const submittableAnswers = {};
    Object.entries(answers).forEach(([qId, answer]) => {
      submittableAnswers[qId] = Array.isArray(answer)
        ? answer.sort().join(",")
        : answer;
    });

    setSubmitting(true);
    const toastId = toast.loading("Submitting...");
    try {
      const res = await submitQuiz(quizId, {
        student_id: studentId,
        answers: submittableAnswers,
      });
      toast.dismiss(toastId);
      toast.success(
        res.data?.message ||
          (res.data?.xp_awarded > 0
            ? `+${res.data.xp_awarded} XP earned!`
            : "Quiz submitted")
      );
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
    const sq = shuffle(quiz.questions || []).map(buildShuffledQuestion);
    setShuffledQuestions(sq);
  };

  if (loading)
    return (
      <div className="panel">
        <Spinner text="Loading..." />
      </div>
    );
  if (result) return <ReviewScreen quiz={quiz} result={result} onRetake={onRetake} />;

  const shuffledQ = shuffledQuestions[currentIndex];
  if (!shuffledQ) return null;
  const total = shuffledQuestions.length;
  const progress = ((currentIndex + 1) / total) * 100;
  const isMulti = shuffledQ.is_multi_select;

  // Current answer for this question (real letters)
  const currentAnswer = answers[shuffledQ.id];
  const currentAnswerArr = Array.isArray(currentAnswer)
    ? currentAnswer
    : currentAnswer
      ? [currentAnswer]
      : [];

  // Jump grid answered count
  const answeredCount = Object.keys(answers).length;

  return (
    <section className="space-y-4">
      <div>
        <div className="mb-1 flex justify-between text-sm text-slate-500">
          <span>
            Question {currentIndex + 1} of {total}
          </span>
          <span>{answeredCount} answered</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className="h-2 rounded-full bg-blue-600 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        {isMulti && (
          <p className="mb-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
            Select all that apply
          </p>
        )}
        <p className="mb-4 font-semibold text-slate-900 dark:text-slate-100">
          {currentIndex + 1}. {shuffledQ.question_text}
        </p>

        <div className="space-y-2">
          {shuffledQ.shuffledOptions.map(({ display, text, realLetter }) => {
            const selected = isMulti
              ? currentAnswerArr.includes(realLetter)
              : currentAnswer === realLetter;

            return (
              <label
                key={display}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all ${
                  selected
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                    : "border-slate-200 hover:border-slate-300 dark:border-slate-700"
                }`}
              >
                <input
                  type={isMulti ? "checkbox" : "radio"}
                  className="sr-only"
                  name={`q_${shuffledQ.id}`}
                  checked={selected}
                  onChange={() => selectAnswer(shuffledQ.id, display, shuffledQ)}
                />
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center border text-sm font-bold transition-all ${
                    isMulti ? "rounded" : "rounded-full"
                  } ${
                    selected
                      ? "border-blue-500 bg-blue-600 text-white"
                      : "border-slate-300 dark:border-slate-600"
                  }`}
                >
                  {selected && isMulti ? "?" : display}
                </span>
                <span className="text-sm text-slate-800 dark:text-slate-200">
                  {text}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {shuffledQuestions.map((q, idx) => (
          <button
            key={q.id}
            onClick={() => setCurrentIndex(idx)}
            className={`h-8 w-8 rounded text-xs font-bold transition-all ${
              idx === currentIndex
                ? "bg-blue-600 text-white"
                : answers[q.id] !== undefined
                  ? "bg-green-500 text-white"
                  : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
            }`}
          >
            {idx + 1}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        {currentIndex > 0 && (
          <button
            className="btn-secondary flex-1"
            onClick={() => setCurrentIndex((i) => i - 1)}
          >
            Previous
          </button>
        )}
        {currentIndex < total - 1 ? (
          <button
            className="btn-primary flex-1"
            onClick={() => setCurrentIndex((i) => i + 1)}
          >
            Next
          </button>
        ) : (
          <button
            className="btn-primary flex-1"
            onClick={onSubmit}
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "Submit Quiz"}
          </button>
        )}
      </div>
    </section>
  );
}
