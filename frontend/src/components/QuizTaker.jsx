import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";

import {
  checkPracticeAnswer,
  completePractice,
  getQuiz,
  saveQuizAssessment,
  startQuizAssessment,
  submitQuiz,
  submitQuizAssessment,
} from "../services/api";
import ActivityAccessError from "./ActivityAccessError";
import QuizReviewScreen from "./QuizReviewScreen";
import Spinner from "./Spinner";

const LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const draftKey = (studentId, quizId, attemptId) =>
  `nexus:quiz-draft:${studentId}:${quizId}:${attemptId}`;

export function hasAnswer(answer) {
  return Array.isArray(answer) ? answer.length > 0 : Boolean(String(answer || "").trim());
}

function serializeAnswers(answers) {
  return Object.fromEntries(
    Object.entries(answers)
      .filter(([, value]) => hasAnswer(value))
      .map(([id, value]) => [id, Array.isArray(value) ? value.join(",") : value]),
  );
}

function sourceQuestions(quiz) {
  return (quiz?.questions || []).map((question, position) => ({
    ...question,
    position,
    options: LETTERS.map((letter) => ({
      letter,
      text: question[`option_${letter.toLowerCase()}`],
    })).filter((option) => option.text),
  }));
}

function readDraft(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "null");
  } catch {
    localStorage.removeItem(key);
    return null;
  }
}

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saveState, setSaveState] = useState("saved");
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timings, setTimings] = useState({});
  const [practiceComplete, setPracticeComplete] = useState(false);
  const [practiceSaving, setPracticeSaving] = useState(false);
  const questionStartRef = useRef(Date.now());
  const loadSequence = useRef(0);
  const saveSequence = useRef(0);
  const revisionRef = useRef(0);
  const saveQueueRef = useRef(Promise.resolve());

  const isAssessment = Boolean(quiz?.is_required && quiz?.show_in_weekly_checklist);
  const storageKey = attempt ? draftKey(studentId, quizId, attempt.id) : null;

  const loadQuiz = async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setLoadError("");
    try {
      const detail = await getQuiz(quizId, studentId, { suppressToast: true });
      if (sequence !== loadSequence.current) return;
      const nextQuiz = detail.data;
      setQuiz(nextQuiz);
      if (nextQuiz.is_required && nextQuiz.show_in_weekly_checklist) {
        const response = await startQuizAssessment(quizId, studentId, { suppressToast: true });
        if (sequence !== loadSequence.current) return;
        const serverAttempt = response.data.attempt;
        const key = draftKey(studentId, quizId, serverAttempt.id);
        const local = readDraft(key);
        const restoredAnswers = { ...(serverAttempt.answers || {}), ...(local?.answers || {}) };
        const restoredPosition = Math.min(
          local?.current_position ?? serverAttempt.current_position ?? 0,
          Math.max(response.data.questions.length - 1, 0),
        );
        setAttempt(serverAttempt);
        revisionRef.current = serverAttempt.revision || 0;
        setQuestions(response.data.questions);
        setAnswers(restoredAnswers);
        setCurrentIndex(restoredPosition);
        if (local) {
          saveQueueRef.current = saveQuizAssessment(
            quizId,
            serverAttempt.id,
            { student_id: studentId, answers: serializeAnswers(restoredAnswers), current_position: restoredPosition, revision: revisionRef.current },
            { suppressToast: true },
          ).then((saved) => { revisionRef.current = saved.data.revision; setSaveState("saved"); }).catch(() => setSaveState("error"));
        }
      } else {
        setQuestions(sourceQuestions(nextQuiz));
        setAttempt(null);
        setAnswers({});
        setCurrentIndex(0);
      }
      setResult(null);
      setFeedback({});
      setPracticeComplete(false);
      setTimings({});
      questionStartRef.current = Date.now();
    } catch (error) {
      if (sequence !== loadSequence.current) return;
      setLoadError(error);
      toast.error(error?.userMessage || "Unable to load quiz");
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  };

  useEffect(() => {
    loadQuiz();
    return () => { loadSequence.current += 1; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId, studentId]);

  useEffect(() => { questionStartRef.current = Date.now(); }, [currentIndex]);

  const persistAssessment = async (nextAnswers, nextPosition) => {
    if (!attempt || !storageKey) return;
    const sequence = ++saveSequence.current;
    const payload = { answers: nextAnswers, current_position: nextPosition };
    const serverAnswers = serializeAnswers(nextAnswers);
    localStorage.setItem(storageKey, JSON.stringify(payload));
    setSaveState("saving");
    saveQueueRef.current = saveQueueRef.current.catch(() => null).then(async () => {
      const saved = await saveQuizAssessment(
        quizId,
        attempt.id,
        { student_id: studentId, answers: serverAnswers, current_position: nextPosition, revision: revisionRef.current },
        { suppressToast: true },
      );
      revisionRef.current = saved.data.revision;
      if (sequence === saveSequence.current) setSaveState("saved");
    }).catch(() => { if (sequence === saveSequence.current) setSaveState("error"); });
    await saveQueueRef.current;
  };

  const selectAnswer = (question, letter) => {
    const current = answers[String(question.id)] ?? answers[question.id];
    let value;
    if (question.is_multi_select) {
      const selected = Array.isArray(current) ? current : String(current || "").split(",").filter(Boolean);
      value = selected.includes(letter) ? selected.filter((item) => item !== letter) : [...selected, letter].sort();
    } else value = letter;
    const next = { ...answers, [String(question.id)]: value };
    setAnswers(next);
    if (isAssessment) void persistAssessment(next, currentIndex);
  };

  const moveTo = (index) => {
    const question = questions[currentIndex];
    if (question) {
      const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
      setTimings((previous) => ({ ...previous, [String(question.id)]: (previous[String(question.id)] || 0) + elapsed }));
    }
    setCurrentIndex(index);
    if (isAssessment) void persistAssessment(answers, index);
  };

  const checkPractice = async () => {
    const question = questions[currentIndex];
    const raw = answers[String(question.id)];
    if (!hasAnswer(raw)) return;
    try {
      const response = await checkPracticeAnswer(
        quizId,
        { student_id: studentId, question_id: question.id, answer: Array.isArray(raw) ? raw.join(",") : raw },
        { suppressToast: true },
      );
      setFeedback((previous) => ({ ...previous, [question.id]: response.data }));
    } catch (error) {
      toast.error(error?.userMessage || "Couldn't check that answer. Try again.");
    }
  };

  const submit = async () => {
    if (submitting) return;
    const unanswered = questions.filter((question) => !hasAnswer(answers[String(question.id)])).length;
    if (unanswered && !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)) return;
    const submittable = serializeAnswers(answers);
    setSubmitting(true);
    try {
      if (isAssessment) await saveQueueRef.current;
      const response = isAssessment
        ? await submitQuizAssessment(quizId, attempt.id, { student_id: studentId, answers: submittable, time_per_question: timings }, { suppressToast: true })
        : await submitQuiz(quizId, { student_id: studentId, answers: submittable, time_per_question: timings }, { suppressToast: true });
      if (storageKey) localStorage.removeItem(storageKey);
      setResult({ ...response.data, purpose: isAssessment ? "assessment" : "practice" });
      toast.success(isAssessment && response.data.passed ? "Assessment passed" : "Responses saved");
    } catch (error) {
      toast.error(error?.userMessage || "Submit failed — your answers are still here. Try again.");
    } finally { setSubmitting(false); }
  };

  const finishPractice = async () => {
    if (practiceSaving) return;
    setPracticeSaving(true);
    try {
      await completePractice(
        quizId,
        {
          student_id: studentId,
          checked_question_ids: questions
            .filter((question) => feedback[question.id])
            .map((question) => question.id),
        },
        { suppressToast: true },
      );
      setPracticeComplete(true);
    } catch (error) {
      toast.error(error?.userMessage || "Check each practice answer before finishing.");
    } finally {
      setPracticeSaving(false);
    }
  };

  const answeredCount = useMemo(() => questions.filter((question) => hasAnswer(answers[String(question.id)])).length, [answers, questions]);

  if (loading) return <div className="panel"><Spinner text="Loading..." /></div>;
  if (loadError || !quiz) return <ActivityAccessError error={loadError} kind="Quiz" onRetry={loadQuiz} />;
  if (result) return <QuizReviewScreen quiz={quiz} result={result} onRetake={() => loadQuiz()} />;
  if (practiceComplete) return (
    <section className="panel space-y-4" aria-live="polite">
      <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Practice complete</p>
      <h2 className="text-2xl font-bold">Keep learning from the feedback</h2>
      <p>This practice does not affect module credit. Review any missed ideas, then practice again whenever it helps.</p>
      <button className="btn-primary" type="button" onClick={() => { setPracticeComplete(false); setAnswers({}); setFeedback({}); setCurrentIndex(0); }}>Practice again</button>
    </section>
  );

  const question = questions[currentIndex];
  if (!question) return null;
  const rawAnswer = answers[String(question.id)];
  const selected = Array.isArray(rawAnswer) ? rawAnswer : rawAnswer ? [rawAnswer] : [];
  const questionFeedback = feedback[question.id];

  return (
    <section className="space-y-4">
      <header className={`rounded-xl border p-4 ${isAssessment ? "border-indigo-300 bg-indigo-50 dark:border-indigo-800 dark:bg-indigo-950/30" : "border-teal-300 bg-teal-50 dark:border-teal-800 dark:bg-teal-950/30"}`}>
        <p className="text-xs font-bold uppercase tracking-wide">{isAssessment ? "Assessment" : "Practice Check"}</p>
        <h2 className="mt-1 text-xl font-bold">{quiz.title}</h2>
        <p className="mt-1 text-sm">{isAssessment ? "Counts toward module completion. Answer independently; feedback appears after submission." : "Learn from mistakes · does not affect module credit"}</p>
        {isAssessment ? <p className="mt-2 text-xs" aria-live="polite">{saveState === "saving" ? "Saving answers…" : saveState === "error" ? "Couldn't save to the server. Your browser draft is still here; change an answer or navigate to retry." : "Answers saved"}</p> : null}
      </header>

      <div className="flex justify-between text-sm text-slate-500"><span>Question {currentIndex + 1} of {questions.length}</span><span>{answeredCount} answered</span></div>
      <div className="panel min-w-0 space-y-4 dark:border-slate-700 dark:bg-slate-900">
        {question.is_multi_select ? <p className="text-xs font-semibold text-amber-600">Select all that apply</p> : null}
        <p className="font-semibold text-slate-900 dark:text-slate-100">{currentIndex + 1}. {question.question_text}</p>
        <div className="space-y-2">
          {question.options.map((option) => {
            const isSelected = selected.includes(option.letter);
            return (
              <label key={option.letter} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${isSelected ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30" : "border-slate-200 dark:border-slate-700"}`}>
                <input className="sr-only" type={question.is_multi_select ? "checkbox" : "radio"} checked={isSelected} onChange={() => selectAnswer(question, option.letter)} />
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${isSelected ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300"}`}>{isSelected && question.is_multi_select ? "✓" : option.letter}</span>
                <span className="min-w-0 break-words text-sm">{option.text}</span>
              </label>
            );
          })}
        </div>
        {!isAssessment && hasAnswer(rawAnswer) && !questionFeedback ? <button type="button" className="btn-primary" onClick={checkPractice}>Check answer</button> : null}
        {questionFeedback ? (
          <div className={`rounded-lg border p-4 text-sm ${questionFeedback.is_correct ? "border-green-300 bg-green-50" : "border-amber-300 bg-amber-50"}`} aria-live="polite">
            <p className="font-bold">{questionFeedback.is_correct ? "That fits" : "Not quite — learn from this"}</p>
            <p className="mt-2"><strong>Your answer:</strong> {questionFeedback.your_answer}</p>
            <p><strong>Correct answer:</strong> {questionFeedback.correct_answer}</p>
            <p className="mt-2"><strong>Key idea:</strong> {questionFeedback.key_idea}</p>
            {questionFeedback.review ? <a className="mt-2 inline-block text-blue-700 underline" href={questionFeedback.review.url}>Review: {questionFeedback.review.label}</a> : null}
          </div>
        ) : null}
      </div>

      <nav className="flex flex-wrap gap-1" aria-label="Question navigation">
        {questions.map((item, index) => {
          const answered = hasAnswer(answers[String(item.id)]);
          return <button type="button" key={item.id} onClick={() => moveTo(index)} className={`h-9 w-9 rounded text-xs font-bold ${index === currentIndex ? "bg-blue-600 text-white" : answered ? "bg-green-500 text-white" : "bg-slate-200 text-slate-600"}`} aria-label={`Go to question ${index + 1}${answered ? ", answered" : ""}`}>{index + 1}</button>;
        })}
      </nav>

      <div className="flex flex-col gap-2 sm:flex-row">
        {currentIndex > 0 ? <button type="button" className="btn-secondary flex-1" onClick={() => moveTo(currentIndex - 1)}>Previous</button> : null}
        {currentIndex < questions.length - 1 ? <button type="button" className="btn-primary flex-1" onClick={() => moveTo(currentIndex + 1)}>Next</button> : isAssessment ? <button type="button" className="btn-primary flex-1" disabled={submitting} onClick={submit}>{submitting ? "Submitting…" : "Submit assessment"}</button> : <button type="button" className="btn-primary flex-1" disabled={practiceSaving} onClick={finishPractice}>{practiceSaving ? "Saving practice…" : "Finish practice"}</button>}
      </div>
    </section>
  );
}
