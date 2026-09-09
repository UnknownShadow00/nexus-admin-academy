import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { AttemptResult } from "../components/AssessmentEvidence";
import { activityOrigin, withActivityOrigin } from "../utils/activityOrigin";
import BackLink from "../components/BackLink";
import { getCurrentStudent } from "../hooks/useAuth";
import Spinner from "../components/Spinner";
import { getQuizReview } from "../services/api";

const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

function normalizeAnswers(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  if (!value) return [];
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildOptions(row, question) {
  const rowOptions = row?.options || {};
  return OPTION_LETTERS.map((letter) => ({
    letter,
    text: rowOptions[letter] || question[`option_${letter.toLowerCase()}`] || "",
  })).filter((option) => option.text);
}

function OptionRow({ letter, text, correctAnswers, studentAnswers }) {
  const isCorrect = correctAnswers.includes(letter);
  const isStudentPick = studentAnswers.includes(letter);
  const isStudentWrong = isStudentPick && !isCorrect;

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
      {isCorrect && isStudentPick ? <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400">Correct</span> : null}
      {isCorrect && !isStudentPick ? <span className="ml-auto text-xs font-bold text-green-600 dark:text-green-400">Correct answer</span> : null}
      {isStudentWrong ? <span className="ml-auto text-xs font-bold text-red-600 dark:text-red-400">Your answer</span> : null}
    </div>
  );
}

export default function QuizReviewPage() {
  const { quizId } = useParams();
  const location = useLocation();
  const origin = activityOrigin(location);
  const attemptId = new URLSearchParams(location.search).get("attempt_id");
  const studentId = getCurrentStudent()?.id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getQuizReview(quizId, studentId, undefined, attemptId)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch(() => { if (!cancelled) setError("No attempt found. Take the quiz first."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [quizId, studentId, attemptId]);

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
        <BackLink className="mt-3 inline-flex text-blue-600" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />
      </main>
    );
  }

  const { title, score, total, xp_awarded: xpAwarded, results, questions } = data;
  const pct = data.percentage;
  const hidesKey = data.purpose === "assessment" && data.disclosure === "concepts_only";
  const byId = {};
  (results || []).forEach((row) => {
    byId[row.question_id] = row;
  });

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <BackLink className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />

      <div className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-8 text-center text-white shadow-lg">
        <h1 className="mb-3 text-lg font-semibold text-blue-200">{title}</h1>
        <p className="text-7xl font-bold">
          {score}
          <span className="text-4xl text-blue-300">/{total}</span>
        </p>
        <p className="mt-2 text-2xl font-semibold">{pct == null ? "Percentage unavailable" : `${pct}%`}</p>
        {xpAwarded > 0 ? <p className="mt-2 text-blue-100">+{xpAwarded} XP earned</p> : null}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-green-600">{score}</p>
          <p className="text-xs text-slate-500">Correct</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-red-500">{pct == null ? "Unavailable" : total - score}</p>
          <p className="text-xs text-slate-500">Wrong</p>
        </div>
        <div className="rounded-lg border p-4 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-2xl font-bold text-blue-600">{pct == null ? "Percentage unavailable" : `${pct}%`}</p>
          <p className="text-xs text-slate-500">Score</p>
        </div>
      </div>

      <section className="panel space-y-2">
        <p>{data.review_selection === "latest" ? "Latest attempt" : "Historical attempt"}: #{data.attempt_id} · {data.passed == null ? "Pass state unavailable" : data.passed ? "Passed" : "Not passed"}</p>
        <p>{data.submitted_at ? new Date(data.submitted_at).toLocaleString() : "Submission time unavailable"} · Passing score: {data.passing_percentage}%</p>
        <p>Best result: <AttemptResult attempt={data.best_attempt} /></p>
        <p>{data.earned_pass ? "Passing requirement earned" : "Passing requirement not yet earned"}</p>
        {data.legacy_passing_credit ? <p>Prior passing credit retained; the original passing attempt is unavailable.</p> : null}
        {data.score_basis === "current_bank_legacy_estimate" ? <p>Historical question total is estimated from the current quiz. Original answer review is unavailable.</p> : null}
        <nav aria-label="Attempt history" className="flex flex-wrap gap-3">{(data.attempts || []).map((attempt, index) => <Link key={attempt.attempt_id} className="text-blue-600" aria-current={attempt.attempt_id === data.attempt_id ? "page" : undefined} to={withActivityOrigin(`/quizzes/${quizId}/review?attempt_id=${attempt.attempt_id}`, origin?.route, origin?.label)} state={location.state}>Attempt {index+1}: {attempt.percentage == null ? "Unknown percentage" : `${attempt.percentage}%`} · {attempt.passed == null ? "Pass state unavailable" : attempt.passed ? "Passed" : "Not passed"}</Link>)}</nav>
      </section>
      {hidesKey ? <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm"><h2 className="font-bold">Review before another graded attempt</h2><p>Exact answers remain hidden because the current bank cannot produce a materially independent retry.</p></section> : null}
      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{hidesKey ? "Review recommendations" : "Answer Review"}</h2>
      {(questions || []).map((question, index) => {
        const row = byId[question.id];
        const studentAnswers = normalizeAnswers(row?.student_answer);
        const correctAnswers = normalizeAnswers(row?.correct_answers || row?.correct_answer || question.correct_answers || question.correct_answer);
        const isCorrect = row?.is_correct;
        const options = buildOptions(row, question);

        return (
          <div
            key={question.id}
            className={`rounded-xl border p-5 ${
              isCorrect ? "border-green-200 dark:border-green-900" : studentAnswers.length ? "border-red-200 dark:border-red-900" : "border-slate-200 dark:border-slate-700"
            }`}
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <p className="font-semibold text-slate-900 dark:text-slate-100">
                Q{index + 1}. {question.question_text}
              </p>
              <span className={`shrink-0 text-lg font-bold ${isCorrect ? "text-green-600" : studentAnswers.length ? "text-red-500" : "text-slate-400"}`}>
                {isCorrect ? "✓" : studentAnswers.length ? "✗" : "—"}
              </span>
            </div>
            <div className="space-y-2">
              {options.map((option) => (
                <OptionRow
                  key={option.letter}
                  letter={option.letter}
                  text={option.text}
                  correctAnswers={correctAnswers}
                  studentAnswers={studentAnswers}
                />
              ))}
            </div>
            {!studentAnswers.length ? <p className="mt-2 text-xs italic text-slate-400">Not answered</p> : null}
            {!isCorrect && row?.student_answer_text ? <p className="mt-3 text-sm"><strong>Your answer:</strong> {row.student_answer_text}</p> : null}
            {!isCorrect && row?.key_idea ? <p className="mt-2 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800"><strong>Key idea:</strong> {row.key_idea}</p> : null}
            {!isCorrect && row?.review ? <Link className="mt-2 inline-block text-sm text-blue-700 underline" to={row.review.url}><strong>Review:</strong> {row.review.label}</Link> : null}
            {row?.explanation ? (
              <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">Tip: {row.explanation}</p>
            ) : null}
          </div>
        );
      })}

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link to={withActivityOrigin(`/quizzes/${quizId}`, origin?.route, origin?.label)} state={location.state} className="btn-primary flex-1 text-center">
          {data.purpose === "assessment" ? "Retry assessment" : "Practice again"}
        </Link>
        <BackLink className="btn-secondary flex-1 justify-center text-center" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />
      </div>
    </main>
  );
}
