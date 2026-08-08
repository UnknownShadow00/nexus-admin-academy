import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { getQuiz, submitQuiz } from "../services/api";
import QuizReviewScreen from "./QuizReviewScreen";
import Spinner from "./Spinner";

const progressKey = (id) => `quiz_progress_${id}`;

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
  const rawOpts = ["A", "B", "C", "D", "E", "F", "G", "H"]
    .map((letter) => ({ letter, text: question[`option_${letter.toLowerCase()}`] }))
    .filter((o) => o.text);

  const shuffled = shuffle(rawOpts);

  // Map display letters to the original answer letters.
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

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [shuffledQuestions, setShuffledQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timings, setTimings] = useState({});
  const questionStartRef = useRef(Date.now());

  const loadQuiz = () => {
    setLoading(true);
    setLoadError("");
    getQuiz(quizId, studentId, { suppressToast: true })
      .then((res) => {
        const q = res.data;
        setQuiz(q);
        const sq = shuffle(q.questions || []).map(buildShuffledQuestion);
        setShuffledQuestions(sq);
        let saved = null;
        try {
          saved = JSON.parse(localStorage.getItem(progressKey(quizId)) || "null");
        } catch {
          localStorage.removeItem(progressKey(quizId));
        }
        setAnswers(saved?.answers || {});
        setCurrentIndex(0);
        setResult(null);
        setTimings({});
        questionStartRef.current = Date.now();
      })
      .catch((err) => {
        const message = err?.userMessage || "Unable to load quiz";
        setLoadError(message);
        toast.error(message);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadQuiz();
    // loadQuiz intentionally restarts only when the quiz or student changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId, studentId]);

  useEffect(() => {
    questionStartRef.current = Date.now();
  }, [currentIndex]);

  const recordCurrentTiming = () => {
    const currentQuestion = shuffledQuestions[currentIndex];
    if (!currentQuestion) return;
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    setTimings((prev) => ({
      ...prev,
      [String(currentQuestion.id)]: (prev[String(currentQuestion.id)] || 0) + elapsed,
    }));
    questionStartRef.current = Date.now();
  };

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
    if (submitting) return;
    const unanswered =
      (shuffledQuestions.length || 0) - shuffledQuestions.filter((question) => {
        const answer = answers[question.id];
        return Array.isArray(answer) ? answer.length > 0 : Boolean(answer);
      }).length;
    if (
      unanswered > 0 &&
      !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)
    )
      return;

    const currentQuestion = shuffledQuestions[currentIndex];
    const lastElapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    const finalTimings = currentQuestion
      ? { ...timings, [String(currentQuestion.id)]: (timings[String(currentQuestion.id)] || 0) + lastElapsed }
      : { ...timings };

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
        time_per_question: finalTimings,
      });
      toast.dismiss(toastId);
      const message =
        res.data?.message ||
        (res.data?.xp_awarded > 0
          ? `+${res.data.xp_awarded} XP earned!`
          : "Quiz submitted");
      if (res.data?.passed) toast.success(message);
      else toast(message);
      setResult(res.data);
      localStorage.removeItem(progressKey(quizId));
    } catch {
      toast.dismiss(toastId);
      toast.error("Submit failed - try again");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading)
    return (
      <div className="panel">
        <Spinner text="Loading..." />
      </div>
    );
  if (!quiz) {
    return (
      <div className="panel">
        <p role="alert" className="text-sm text-slate-600 dark:text-slate-300">{loadError || "Quiz is unavailable right now."}</p>
        <button type="button" className="btn-primary mt-4" onClick={loadQuiz}>Try again</button>
      </div>
    );
  }
  if (result) return <QuizReviewScreen quiz={quiz} result={result} onRetake={() => { setResult(null); setAnswers({}); setTimings({}); setCurrentIndex(0); questionStartRef.current = Date.now(); }} />;

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
        <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
          Choose {isMulti ? "all correct answers" : "one answer"}, then use Next. Submit once at the end to see your score and explanations.
        </p>
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
                  {selected && isMulti ? "✓" : display}
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
            type="button"
            key={q.id}
            onClick={() => {
              recordCurrentTiming();
              setCurrentIndex(idx);
            }}
            className={`h-8 w-8 rounded text-xs font-bold transition-all ${
              idx === currentIndex
                ? "bg-blue-600 text-white"
                : answers[q.id] !== undefined
                  ? "bg-green-500 text-white"
                  : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
            }`}
            aria-label={`Go to question ${idx + 1}${answers[q.id] !== undefined ? ", answered" : ""}`}
            aria-current={idx === currentIndex ? "step" : undefined}
          >
            {idx + 1}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        {currentIndex > 0 && (
          <button
            type="button"
            className="btn-secondary flex-1"
            onClick={() => {
              recordCurrentTiming();
              setCurrentIndex((i) => i - 1);
            }}
          >
            Previous
          </button>
        )}
        {currentIndex < total - 1 ? (
          <button
            type="button"
            className="btn-primary flex-1"
            onClick={() => {
              recordCurrentTiming();
              setCurrentIndex((i) => i + 1);
            }}
          >
            Next
          </button>
        ) : (
          <button
            type="button"
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
