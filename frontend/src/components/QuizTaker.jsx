import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { getQuiz, submitQuiz } from "../services/api";
import { clearQuizDraft, hasAnswer, OPTION_LETTERS, readQuizDraft, writeQuizDraft } from "../utils/quizDraft";
import QuizReviewScreen from "./QuizReviewScreen";
import Spinner from "./Spinner";

function shuffle(arr) {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function buildShuffledQuestion(question, savedOrder) {
  const letters = savedOrder || shuffle(OPTION_LETTERS.filter((letter) => question[`option_${letter.toLowerCase()}`]));
  return {
    ...question,
    shuffledOptions: letters.map((realLetter, index) => ({
      display: String.fromCharCode(65 + index),
      text: question[`option_${realLetter.toLowerCase()}`],
      realLetter,
    })),
  };
}

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timings, setTimings] = useState({});
  const [resumed, setResumed] = useState(false);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const questionStartRef = useRef(Date.now());
  const loadVersionRef = useRef(0);
  const loadedScopeRef = useRef(null);
  const submittingRef = useRef(false);
  const questionHeadingRef = useRef(null);
  const moveFocusRef = useRef(false);

  const loadQuiz = () => {
    const version = ++loadVersionRef.current;
    loadedScopeRef.current = null;
    submittingRef.current = false;
    setLoading(true);
    setLoadError("");
    setSubmitError("");
    setSubmitting(false);
    setQuiz(null);
    getQuiz(quizId, studentId, { suppressToast: true })
      .then((response) => {
        if (version !== loadVersionRef.current) return;
        const nextQuiz = response.data;
        loadedScopeRef.current = `${studentId}:${quizId}`;
        const { draft, available } = readQuizDraft(studentId, quizId, nextQuiz);
        const byId = new Map((nextQuiz.questions || []).map((question) => [question.id, question]));
        const order = draft?.order || shuffle([...byId.keys()]);
        setQuiz(nextQuiz);
        setQuestions(order.map((id) => buildShuffledQuestion(byId.get(id), draft?.options[id])));
        setAnswers(draft?.answers || {});
        setCurrentIndex(draft?.currentIndex || 0);
        setTimings(draft?.timings || {});
        setResumed(Boolean(draft && (Object.values(draft.answers).some(hasAnswer) || draft.currentIndex > 0)));
        setStorageAvailable(available);
        setResult(null);
        questionStartRef.current = Date.now();
      })
      .catch((error) => {
        if (version === loadVersionRef.current) setLoadError(error?.userMessage || "Unable to load this quiz. Try again.");
      })
      .finally(() => {
        if (version === loadVersionRef.current) setLoading(false);
      });
  };

  useEffect(() => {
    loadQuiz();
    return () => { loadVersionRef.current += 1; };
    // Each quiz/account owns one request generation and draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId, studentId]);

  useEffect(() => {
    if (loading || !quiz || result || !questions.length || loadedScopeRef.current !== `${studentId}:${quizId}`) return;
    setStorageAvailable(writeQuizDraft(studentId, quizId, quiz, questions, answers, currentIndex, timings));
  }, [answers, currentIndex, loading, questions, quiz, quizId, result, studentId, timings]);

  useEffect(() => {
    if (loading || result) return;
    questionStartRef.current = Date.now();
    if (moveFocusRef.current) {
      questionHeadingRef.current?.focus({ preventScroll: true });
      questionHeadingRef.current?.scrollIntoView?.({ block: "nearest" });
      moveFocusRef.current = false;
    }
  }, [currentIndex, loading, result]);

  const navigateQuestion = (index) => {
    if (submittingRef.current) return;
    const question = questions[currentIndex];
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    if (question) setTimings((previous) => ({ ...previous, [question.id]: (previous[question.id] || 0) + elapsed }));
    questionStartRef.current = Date.now();
    moveFocusRef.current = true;
    setCurrentIndex(index);
    if (index === currentIndex) questionHeadingRef.current?.focus();
  };

  const selectAnswer = (question, letter) => {
    if (submittingRef.current) return;
    setAnswers((previous) => {
      if (!question.is_multi_select) return { ...previous, [question.id]: letter };
      const current = Array.isArray(previous[question.id]) ? previous[question.id] : [];
      return { ...previous, [question.id]: current.includes(letter) ? current.filter((value) => value !== letter) : [...current, letter].sort() };
    });
  };

  const onSubmit = async () => {
    if (submittingRef.current) return;
    const unanswered = questions.filter((question) => !hasAnswer(answers[question.id])).length;
    if (unanswered && !window.confirm(`${unanswered} unanswered question(s). Submit anyway?`)) return;
    submittingRef.current = true;
    const version = loadVersionRef.current;
    const question = questions[currentIndex];
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    const finalTimings = { ...timings, [question.id]: (timings[question.id] || 0) + elapsed };
    setTimings(finalTimings);
    questionStartRef.current = Date.now();
    setSubmitting(true);
    setSubmitError("");
    try {
      const response = await submitQuiz(quizId, {
        student_id: studentId,
        answers: Object.fromEntries(Object.entries(answers).map(([id, answer]) => [id, Array.isArray(answer) ? [...answer].sort().join(",") : answer])),
        time_per_question: finalTimings,
      }, { suppressToast: true });
      if (version !== loadVersionRef.current) return;
      setResult(response.data);
      // Keep the draft's attempt generation current when the learner chooses
      // a deliberate retake without reloading the quiz detail endpoint.
      setQuiz((previous) => ({ ...previous, attempts: [...(previous.attempts || []), { score: response.data.score }] }));
      clearQuizDraft(studentId, quizId);
      toast.success("Quiz submitted. Your answers are ready to review.");
    } catch (error) {
      if (version === loadVersionRef.current) setSubmitError(error?.userMessage || "We could not confirm your submission. Your answers are still here. Try submitting again.");
    } finally {
      if (version === loadVersionRef.current) {
        submittingRef.current = false;
        setSubmitting(false);
      }
    }
  };

  const retake = () => {
    setAnswers({});
    setTimings({});
    setCurrentIndex(0);
    setResumed(false);
    setSubmitError("");
    moveFocusRef.current = true;
    setResult(null);
    questionStartRef.current = Date.now();
  };

  if (loading) return <div className="panel"><Spinner text="Loading quiz..." /></div>;
  if (!quiz) return <div className="panel"><p role="alert">{loadError || "Quiz is unavailable right now."}</p><button type="button" className="btn-primary mt-4" onClick={loadQuiz}>Try again</button></div>;
  if (result) return <QuizReviewScreen quiz={{ ...quiz, questions }} result={result} onRetake={retake} />;
  if (!questions.length) return <div className="panel" role="alert">This quiz has no questions available yet. Return to your module and ask your instructor for help.</div>;

  const question = questions[currentIndex];
  const total = questions.length;
  const currentAnswer = answers[question.id];
  const answeredCount = questions.filter((item) => hasAnswer(answers[item.id])).length;

  return (
    <section className="space-y-4" aria-labelledby="quiz-title" aria-busy={submitting}>
      <header>
        <p className="text-sm font-semibold text-blue-700 dark:text-blue-300">{quiz.week_number === 0 ? "Orientation" : `Week ${quiz.week_number}`} · Knowledge check</p>
        <h1 id="quiz-title" className="mt-1 text-2xl font-bold text-slate-950 dark:text-white">{quiz.title}</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Choose {question.is_multi_select ? "all correct answers" : "one answer"}, then use Next. Submit once at the end to see your score and explanations. You can retry after reviewing.</p>
        {(quiz.attempts?.length || 0) > 0 ? <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Previous attempts are kept. Only your first attempt awards XP; a retry can still improve your best score and progress.</p> : null}
      </header>
      {!storageAvailable ? <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">This browser cannot save your quiz draft. Keep this tab open until you submit.</p> : resumed ? <p role="status" className="text-sm text-slate-600 dark:text-slate-300">Your saved answers and place have been restored on this browser.</p> : <p className="text-xs text-slate-500 dark:text-slate-400">Your answers and place are saved on this browser as you work.</p>}
      <div>
        <div className="mb-1 flex flex-wrap justify-between gap-2 text-sm text-slate-600 dark:text-slate-300"><span>Question {currentIndex + 1} of {total}</span><span aria-live="polite">{answeredCount} answered</span></div>
        <div role="progressbar" aria-label="Quiz question position" aria-valuemin={0} aria-valuemax={total} aria-valuenow={currentIndex + 1} className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-2 rounded-full bg-blue-600 transition-all" style={{ width: `${((currentIndex + 1) / total) * 100}%` }} /></div>
      </div>
      <fieldset className="panel min-w-0 dark:border-slate-700 dark:bg-slate-900" disabled={submitting} aria-describedby="quiz-answer-instruction">
        <legend className="sr-only">Question {currentIndex + 1}: {question.question_text}</legend>
        <h2 ref={questionHeadingRef} tabIndex={-1} className="mb-3 scroll-mt-40 break-words font-semibold text-slate-900 outline-none dark:text-slate-100 sm:scroll-mt-24">{currentIndex + 1}. {question.question_text}</h2>
        <p id="quiz-answer-instruction" className="mb-3 text-sm font-medium text-slate-600 dark:text-slate-300">{question.is_multi_select ? "Select all that apply" : "Select one answer"}</p>
        <div className="space-y-2">
          {question.shuffledOptions.map(({ display, text, realLetter }) => {
            const selected = question.is_multi_select ? (currentAnswer || []).includes(realLetter) : currentAnswer === realLetter;
            return (
              <label key={realLetter} className={`flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors focus-within:ring-2 focus-within:ring-blue-600 focus-within:ring-offset-2 dark:focus-within:ring-blue-300 dark:focus-within:ring-offset-slate-900 ${selected ? "border-blue-600 bg-blue-50 dark:border-blue-400 dark:bg-blue-950/30" : "border-slate-300 hover:border-blue-400 dark:border-slate-600"}`}>
                <input type={question.is_multi_select ? "checkbox" : "radio"} className="sr-only" name={`q_${question.id}`} checked={selected} onChange={() => selectAnswer(question, realLetter)} />
                <span aria-hidden="true" className={`flex h-7 w-7 shrink-0 items-center justify-center border text-sm font-bold ${question.is_multi_select ? "rounded" : "rounded-full"} ${selected ? "border-blue-600 bg-blue-600 text-white" : "border-slate-400 text-slate-700 dark:text-slate-200"}`}>{selected ? "✓" : display}</span>
                <span className="min-w-0 break-words pt-0.5 text-sm text-slate-800 dark:text-slate-200">{text}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      <nav className="flex flex-wrap gap-2" aria-label="Quiz questions">
        {questions.map((item, index) => <button type="button" key={item.id} disabled={submitting} onClick={() => navigateQuestion(index)} className={`h-11 min-w-11 rounded px-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${index === currentIndex ? "bg-blue-600 text-white" : hasAnswer(answers[item.id]) ? "border border-blue-300 bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100" : "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100"}`} aria-label={`Go to question ${index + 1}${hasAnswer(answers[item.id]) ? ", answered" : ", unanswered"}`} aria-current={index === currentIndex ? "step" : undefined}>{index + 1}{hasAnswer(answers[item.id]) ? <span aria-hidden="true"> ✓</span> : null}</button>)}
      </nav>
      {submitError ? <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-100">{submitError}</p> : null}
      <div className="flex gap-3">
        {currentIndex > 0 ? <button type="button" className="btn-secondary min-h-11 flex-1" disabled={submitting} onClick={() => navigateQuestion(currentIndex - 1)}>Previous</button> : null}
        {currentIndex < total - 1 ? <button type="button" className="btn-primary min-h-11 flex-1" disabled={submitting} onClick={() => navigateQuestion(currentIndex + 1)}>Next</button> : <button type="button" className="btn-primary min-h-11 flex-1" onClick={onSubmit} disabled={submitting}>{submitting ? "Submitting..." : "Submit Quiz"}</button>}
      </div>
    </section>
  );
}
