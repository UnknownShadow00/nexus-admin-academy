import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2NextStep from "../../components/v2/V2NextStep";
import QuizLayout, { QuizFrame } from "../../components/academy/QuizLayout";
import { getCurrentStudent } from "../../hooks/useAuth";
import { getV2Assessment, startV2AssessmentAttempt, submitV2Assessment } from "../../services/api";
import { assessmentDraftKey, clearAssessmentDraft, readAssessmentDraft, writeAssessmentDraft } from "../../utils/assessmentDraft";

function answered(value) { return Array.isArray(value) ? value.length > 0 : typeof value === "string" && Boolean(value.trim()); }

export default function V2AssessmentPage() {
  const { moduleKey, assessmentKey } = useParams();
  const studentId = getCurrentStudent()?.id;
  const stageRoute = `/learning-v2/modules/${moduleKey}`;
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [available, setAvailable] = useState(true);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const generation = useRef(0), submitLock = useRef(false), heading = useRef(null), moveFocus = useRef(false), loadedScope = useRef(null);
  const scope = `${studentId}:${moduleKey}:${assessmentKey}`;
  const keys = useCallback(payload => [assessmentDraftKey(studentId, moduleKey, assessmentKey, payload.attempt?.id), `v2_assessment_${studentId}_${assessmentKey}_${payload.attempt?.id}`], [studentId, moduleKey, assessmentKey]);
  const load = useCallback(() => {
    const version = ++generation.current; loadedScope.current = null;
    setError(""); setData(null); setResult(null); setAnswers({}); setIndex(0); setConfirmSubmit(false); setBusy(false); submitLock.current = false;
    getV2Assessment(moduleKey, assessmentKey, { suppressToast: true }).then(res => {
      if (version !== generation.current) return;
      loadedScope.current = scope;
      const [key, oldKey] = keys(res.data);
      const draft = readAssessmentDraft(key, res.data, oldKey);
      setAnswers(draft.answers); setIndex(draft.index); setAvailable(draft.available); setData(res.data); setResult(res.data.result || null);
    }).catch(err => { if (version === generation.current) setError(err?.response?.status === 404 ? "That knowledge check is unavailable. Return to the stage and choose another activity." : err?.userMessage || "The questions could not be loaded."); });
  }, [assessmentKey, moduleKey, keys, scope]);
  useEffect(() => { load(); return () => { generation.current += 1; }; }, [load]);
  useEffect(() => { if (data && !result && loadedScope.current === scope) setAvailable(writeAssessmentDraft(keys(data)[0], data, answers, index)); }, [data, result, keys, answers, index, scope]);
  useEffect(() => { if (moveFocus.current) { heading.current?.focus({ preventScroll: true }); heading.current?.scrollIntoView?.({ block: "nearest" }); moveFocus.current = false; } }, [index]);
  function navigate(next) { if (submitLock.current) return; moveFocus.current = true; setIndex(next); setConfirmSubmit(false); }
  function update(question, value) { if (!submitLock.current) setAnswers(previous => ({ ...previous, [question.id]: value })); }
  function toggle(question, key) { const current = Array.isArray(answers[question.id]) ? answers[question.id] : []; update(question, current.includes(key) ? current.filter(item => item !== key) : [...current, key].sort()); }
  const unansweredIndexes = data?.questions?.map((question, questionIndex) => answered(answers[question.id]) ? null : questionIndex).filter(value => value !== null) || [];
  function requestSubmit() { if (submitLock.current) return; if (unansweredIndexes.length) setConfirmSubmit(true); else void submit(); }
  async function submit() {
    if (submitLock.current || !data) return;
    submitLock.current = true; const version = generation.current;
    setConfirmSubmit(false); setBusy(true); setError("");
    try {
      const res = await submitV2Assessment(moduleKey, assessmentKey, data.attempt.id, answers, { suppressToast: true });
      if (version !== generation.current) return;
      setResult(res.data); clearAssessmentDraft(...keys(data));
    } catch (err) { if (version === generation.current) setError(err?.userMessage || "We couldn't save your answers. Your work is still here. Try again."); }
    finally { if (version === generation.current) { submitLock.current = false; setBusy(false); } }
  }
  async function retry() {
    if (submitLock.current) return; submitLock.current = true; const version = generation.current;
    setBusy(true); setError("");
    try {
      const res = await startV2AssessmentAttempt(moduleKey, assessmentKey, { suppressToast: true });
      if (version !== generation.current) return;
      setData(res.data); setResult(res.data.result || null); setAnswers({}); setIndex(0); setConfirmSubmit(false);
    } catch (err) { if (version === generation.current) setError(err?.userMessage || "A new attempt could not be started."); }
    finally { if (version === generation.current) { submitLock.current = false; setBusy(false); } }
  }
  if (error && !data) return <V2Error message={error} onRetry={load} moduleRoute={stageRoute} />;
  if (!data) return <V2Loading text="Loading questions..." />;
  const back = <Link to={stageRoute}>Back to Stage</Link>;
  if (result) {
    const pending = result.grading_state !== "graded" || result.score == null || typeof result.passed !== "boolean";
    const outcome = pending ? "Grading pending" : result.passed ? "Passed" : "Not quite";
    return <QuizFrame>
      <header className="card quiz-header"><p className="eyebrow purple">Assessment results · {pending ? "Awaiting grading" : result.passed ? "Passed assessment" : "Failed assessment"}</p><h1>{data.assessment.title}</h1></header>
      <section className={`card quiz-result-status learning-feedback ${pending ? "" : result.passed ? "learning-feedback-correct" : "learning-feedback-retry"}`} role="status" aria-labelledby="assessment-outcome">
        <h2 id="assessment-outcome">{outcome}</h2>
        <p>{pending ? "Your answers were saved. Grading is still in progress; you do not need to submit again. No final score or mastery is awarded while grading is pending." : `Score: ${result.score}% · Pass mark: ${result.pass_percent}%`}</p>
        <p className="small sub">{pending ? "You can return here to check the server result or continue another available activity." : result.passed ? "Your checkpoint is complete. Follow the next course action below." : "Review the feedback, then start a new attempt when you are ready."}</p>
        {pending ? <button className="btn btn-secondary" type="button" onClick={load}>Check grading status</button> : null}
      </section>
      {result.results?.length ? <section className="card result-review" aria-labelledby="answer-review-title"><h2 id="answer-review-title">Answer review</h2><ol>{result.results.map(item => {
        const waiting = item.grading_status === "needs_review" || item.is_correct == null;
        return <li className="result-row" key={item.question_id}><h3>{item.question_text}</h3><p className="mt-2 font-semibold">{waiting ? "Waiting for grading" : item.is_correct ? "Correct" : "Not quite"}</p>{item.student_answer ? <p className="mt-2 whitespace-pre-wrap"><strong>Your answer: </strong>{item.student_answer}</p> : null}{waiting ? <p className="mt-2">Your wording was saved. Automatic matching could not confidently determine the grade.</p> : null}{!pending && item.correct_answer?.length ? <p className="mt-2 small sub">Correct answer: {item.correct_answer.join(", ")}</p> : null}{!pending && item.explanation ? <p className="mt-2">{item.explanation}</p> : null}</li>;
      })}</ol></section> : null}
      {error ? <p role="alert" className="notice-error rounded-lg p-3">{error}</p> : null}
      <div className="actions">{!pending && result.passed ? <V2NextStep moduleKey={moduleKey} /> : !pending ? <button className="btn btn-primary" disabled={busy} onClick={retry} type="button">{busy ? "Starting..." : "Try again"}</button> : null}{back}</div>
    </QuizFrame>;
  }
  const question = data.questions[index];
  if (!question) return <V2Error title="No questions available" message="This knowledge check has not been configured yet." />;
  const answer = answers[question.id];
  const isText = ["short_answer", "free_response"].includes(question.type);
  return <QuizLayout key={data.attempt.id} title={data.assessment.title} eyebrow={data.assessment.role === "module_quiz" ? "Module Quiz" : "Quick Check"} questions={data.questions} index={index} hasAnswer={item => answered(answers[item.id])} onNavigate={navigate} onSubmit={requestSubmit} busy={busy} headingRef={heading} back={back} error={error} storage={available ? "Saved on this browser. Not submitted to the server yet." : "This browser cannot save your draft. Keep this tab open until you submit."} instruction={isText ? "Use your own words. Saving your answer and passing the assessment are separate steps." : question.is_multi_select ? "Select all that apply. You can revise your selection before submitting." : undefined}>
    <fieldset disabled={busy} className="choices" aria-describedby="checkpoint-question-title"><legend className="sr-only">{isText ? "Written response" : question.is_multi_select ? "Select all that apply" : "Choose one answer"}</legend>
      {isText ? <div><label className="mb-2 block font-semibold" htmlFor={`answer-${question.id}`}>Your answer</label>{question.type === "free_response" ? <textarea id={`answer-${question.id}`} className="input-field min-h-40 w-full" maxLength={10000} value={answer || ""} onChange={event => update(question, event.target.value)} aria-describedby="written-answer-limit" /> : <input id={`answer-${question.id}`} className="input-field w-full" maxLength={10000} value={answer || ""} onChange={event => update(question, event.target.value)} autoComplete="off" aria-describedby="written-answer-limit" />}<p id="written-answer-limit" className="small muted mt-2">Up to 10,000 characters. Your original wording is preserved.</p></div>
        : question.options.map(option => { const selected = question.is_multi_select ? Array.isArray(answer) && answer.includes(option.key) : answer === option.key; return <label className={`choice ${selected ? "selected" : ""}`} key={option.key}><span className="letter">{option.key}.</span><input type={question.is_multi_select ? "checkbox" : "radio"} name={`question-${question.id}`} checked={selected} onChange={() => question.is_multi_select ? toggle(question, option.key) : update(question, option.key)} /><span>{option.text}</span></label>; })}
    </fieldset>
    {confirmSubmit ? <section className="quiz-submit-review" role="alert"><p>You still have {unansweredIndexes.length} unanswered question{unansweredIndexes.length === 1 ? "" : "s"}.</p><div className="actions"><button className="btn btn-secondary" onClick={() => navigate(unansweredIndexes[0])} type="button">Review unanswered</button><button className="btn btn-primary" disabled={busy} onClick={submit} type="button">Submit anyway</button></div></section> : null}
  </QuizLayout>;
}
