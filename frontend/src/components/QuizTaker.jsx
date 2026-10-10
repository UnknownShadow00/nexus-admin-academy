import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { getQuiz, submitQuiz } from "../services/api";
import { clearQuizDraft, hasAnswer, OPTION_LETTERS, readQuizDraft, writeQuizDraft } from "../utils/quizDraft";
import QuizReviewScreen from "./QuizReviewScreen";
import Spinner from "./Spinner";
import QuizLayout, { QuizFrame } from "./academy/QuizLayout";

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

export default function QuizTaker({ quizId, studentId, back }) {
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
        presentation_hash: quiz.presentation_hash,
        presented_questions: questions.map((item) => ({ id: item.id, options: item.shuffledOptions.map((option) => option.realLetter) })),
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
  if (result) return <QuizFrame><QuizReviewScreen quiz={{ ...quiz, questions }} result={result} onRetake={retake} /></QuizFrame>;
  if (!questions.length) return <div className="panel" role="alert">This quiz has no questions available yet. Return to your module and ask your instructor for help.</div>;

  const question = questions[currentIndex];
  const currentAnswer = answers[question.id];

  return (
    <QuizLayout title={quiz.title} eyebrow={`${quiz.week_number === 0 ? "Orientation" : `Week ${quiz.week_number}`} · Knowledge check`}
      questions={questions} index={currentIndex} hasAnswer={item => hasAnswer(answers[item.id])} onNavigate={navigateQuestion} onSubmit={onSubmit} busy={submitting}
      numbered back={back || <a href="/quizzes">Back to Quizzes</a>} headingRef={questionHeadingRef} nextLabel="Next" submitLabel="Submit Quiz" error={submitError}
      instruction={question.is_multi_select ? "Select all that apply. You can revise your selection before submitting." : undefined}
      storage={!storageAvailable ? "This browser cannot save your quiz draft. Keep this tab open until you submit." : resumed ? "Your saved answers and place have been restored on this browser. Not submitted to the server yet." : "Your answers and place are saved on this browser as you work. Not submitted to the server yet."}>
      <fieldset className="choices" disabled={submitting} aria-describedby="quiz-answer-instruction">
        <legend className="sr-only">Question {currentIndex + 1}: {question.question_text}</legend>
        <p id="quiz-answer-instruction" className="mb-3 text-sm font-medium text-slate-600 dark:text-slate-300">{question.is_multi_select ? "Select all that apply" : "Select one answer"}</p>
        <div className="space-y-2">
          {question.shuffledOptions.map(({ display, text, realLetter }) => {
            const selected = question.is_multi_select ? (currentAnswer || []).includes(realLetter) : currentAnswer === realLetter;
            return (
              <label key={realLetter} className={`choice ${selected ? "selected" : ""}`}>
                <input type={question.is_multi_select ? "checkbox" : "radio"} name={`q_${question.id}`} checked={selected} onChange={() => selectAnswer(question, realLetter)} />
                <span aria-hidden="true" className="letter">{selected ? "✓" : display}</span>
                <span className="min-w-0 break-words pt-0.5 text-sm text-slate-800 dark:text-slate-200">{text}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
    </QuizLayout>
  );
}
