import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { OPTION_LETTERS } from "../utils/quizDraft";

function answerLetters(value) {
  if (Array.isArray(value)) return value;
  return value ? String(value).split(",").map((letter) => letter.trim()).filter(Boolean) : [];
}

export default function QuizReviewScreen({ quiz, result, onRetake, retakeLabel = "Try Again" }) {
  const [missedOnly, setMissedOnly] = useState(false);
  const headingRef = useRef(null);
  useEffect(() => {
    setMissedOnly(false);
    headingRef.current?.focus({ preventScroll: true });
    headingRef.current?.parentElement?.scrollIntoView?.({ block: "start" });
  }, [result]);
  const byId = Object.fromEntries((result.results || []).map((row) => [row.question_id, row]));
  const total = result.total || 0;
  const percent = total > 0 ? Math.round((result.score / total) * 100) : 0;
  const rows = (quiz.questions || []).map((question, index) => ({ question, index, review: byId[question.id] }));
  const missed = rows.filter(({ review }) => !review?.is_correct);
  const shown = missedOnly ? missed : rows;
  const passed = result.passed;

  return (
    <section className="space-y-5" aria-labelledby="quiz-result-title">
      <header className="scroll-mt-40 rounded-xl bg-blue-700 p-5 text-white sm:scroll-mt-24 sm:p-6">
        <p className="text-sm font-semibold text-blue-100">Quiz results</p>
        <h1 ref={headingRef} tabIndex={-1} id="quiz-result-title" className="mt-1 text-2xl font-bold outline-none">{quiz.title}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <p className="text-3xl font-bold">{result.score} / {total} <span className="text-xl font-medium text-blue-100">({percent}%)</span></p>
          {typeof passed === "boolean" ? <span className={`rounded-full px-3 py-1 text-sm font-bold ${passed ? "bg-green-100 text-green-900" : "bg-amber-100 text-amber-900"}`}>{passed ? "Passed" : "Not passed"}</span> : null}
        </div>
        <p className="mt-3 text-sm text-blue-50">{missed.length ? `Review ${missed.length === 1 ? "the question" : `the ${missed.length} questions`} below to see what to practice next. You can retry the full quiz when you are ready.` : "You answered every question correctly. Review the reasoning, then continue your learning."}</p>
        {result.message ? <p className="mt-2 text-sm text-blue-100">{result.message}</p> : null}
        {result.xp_awarded > 0 ? <p className="mt-2 text-sm text-blue-100">+{result.xp_awarded} XP earned</p> : null}
      </header>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Link to="/" className="btn-primary min-h-11 text-center">Continue Learning</Link>
        <button type="button" className="btn-secondary min-h-11" onClick={onRetake}>{retakeLabel}</button>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">A retry includes every question. Your previous attempts and best progress are kept.</p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-slate-950 dark:text-white">Answer Review</h2>
        {missed.length ? <button type="button" className="btn-secondary min-h-11" aria-pressed={missedOnly} onClick={() => setMissedOnly((current) => !current)}>{missedOnly ? "Show all questions" : "Review missed questions"}</button> : null}
      </div>
      <p role="status" className="text-sm text-slate-600 dark:text-slate-300">Showing {shown.length} of {rows.length} questions{missedOnly ? " to review" : ""}.</p>
      {shown.map(({ question, index, review }) => {
        const studentAnswers = answerLetters(review?.student_answer);
        const correctAnswers = answerLetters(review?.correct_answers || review?.correct_answer || question.correct_answers || question.correct_answer);
        const correct = Boolean(review?.is_correct);
        const options = review?.options || Object.fromEntries(OPTION_LETTERS.map((letter) => [letter, question[`option_${letter.toLowerCase()}`] || ""]));
        const explanation = review?.explanation || question.explanation;
        const status = correct ? "Correct" : studentAnswers.length ? "Incorrect" : "Not answered";
        return (
          <article key={question.id} className={`min-w-0 rounded-xl border p-4 sm:p-5 ${correct ? "border-green-300 dark:border-green-800" : "border-amber-300 dark:border-amber-800"}`}>
            <p className={`mb-2 text-sm font-semibold ${correct ? "text-green-800 dark:text-green-300" : "text-amber-800 dark:text-amber-200"}`}>{status}</p>
            <h3 className="mb-3 break-words font-semibold text-slate-950 dark:text-slate-100">Q{index + 1}. {review?.question_text || question.question_text}</h3>
            <ul className="space-y-2">
              {OPTION_LETTERS.filter((letter) => options[letter]).map((letter) => {
                const right = correctAnswers.includes(letter);
                const selected = studentAnswers.includes(letter);
                return <li key={letter} className={`min-w-0 rounded-lg border p-3 text-sm ${right ? "border-green-400 bg-green-50 text-green-950 dark:border-green-700 dark:bg-green-950/30 dark:text-green-100" : selected ? "border-red-300 bg-red-50 text-red-950 dark:border-red-700 dark:bg-red-950/30 dark:text-red-100" : "border-slate-200 text-slate-700 dark:border-slate-700 dark:text-slate-300"}`}><p className="break-words">{options[letter]}</p>{right || selected ? <p className="mt-1 text-xs font-semibold">{right && selected ? "Correct answer · Your answer" : right ? "Correct answer" : "Your answer"}</p> : null}</li>;
              })}
            </ul>
            <div className="mt-4 rounded-lg bg-blue-50 p-3 text-sm text-slate-800 dark:bg-blue-950/30 dark:text-slate-100">
              <h4 className="mb-1 font-semibold text-blue-900 dark:text-blue-200">{correct ? "Why this is correct" : "What to remember"}</h4>
              <p className="whitespace-pre-wrap break-words leading-6">{explanation || "An explanation is being reviewed for this question. Use the correct answer above and ask your instructor if the reasoning is unclear."}</p>
            </div>
          </article>
        );
      })}
      <button type="button" className="btn-secondary min-h-11" onClick={() => { headingRef.current?.focus({ preventScroll: true }); headingRef.current?.parentElement?.scrollIntoView?.({ block: "start" }); }}>Back to result summary</button>
    </section>
  );
}
