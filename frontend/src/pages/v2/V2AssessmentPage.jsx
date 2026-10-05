import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2NextStep from "../../components/v2/V2NextStep";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";
import { getCurrentStudent } from "../../hooks/useAuth";
import { getV2Assessment, startV2AssessmentAttempt, submitV2Assessment } from "../../services/api";

function answered(value) { return Array.isArray(value) ? value.length > 0 : Boolean(String(value || "").trim()); }

export default function V2AssessmentPage() {
  const { moduleKey, assessmentKey } = useParams();
  const stageRoute = `/learning-v2/modules/${moduleKey}`;
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const load = useCallback(() => {
    setError("");
    getV2Assessment(moduleKey, assessmentKey, { suppressToast: true }).then((res) => {
      setData(res.data);
      setResult(res.data.result || null);
    }).catch((err) => setError(err?.response?.status === 404
      ? "That knowledge check is unavailable. Return to the stage and choose another activity."
      : err?.userMessage || "The questions could not be loaded."));
  }, [assessmentKey, moduleKey]);
  useEffect(load, [load]);
  const studentId = getCurrentStudent()?.id;
  const storageKey = useMemo(() => data?.attempt?.id && studentId
    ? `v2_assessment_${studentId}_${assessmentKey}_${data.attempt.id}` : null,
  [assessmentKey, data?.attempt?.id, studentId]);
  useEffect(() => {
    if (!storageKey) return;
    try { setAnswers(JSON.parse(localStorage.getItem(storageKey) || "{}")); }
    catch { localStorage.removeItem(storageKey); }
  }, [storageKey]);
  function update(question, value) {
    const next = { ...answers, [question.id]: value };
    setAnswers(next);
    if (storageKey) localStorage.setItem(storageKey, JSON.stringify(next));
  }
  function toggle(question, key) {
    const current = Array.isArray(answers[question.id]) ? answers[question.id] : [];
    update(question, current.includes(key) ? current.filter((item) => item !== key) : [...current, key].sort());
  }
  const unansweredIndexes = data?.questions?.map((question, questionIndex) => answered(answers[question.id]) ? null : questionIndex)
    .filter((value) => value !== null) || [];
  function requestSubmit() {
    if (unansweredIndexes.length) { setConfirmSubmit(true); return; }
    void submit();
  }
  async function submit() {
    setConfirmSubmit(false);
    setBusy(true);
    setError("");
    try {
      const res = await submitV2Assessment(moduleKey, assessmentKey, data.attempt.id, answers, { suppressToast: true });
      setResult(res.data);
      if (storageKey) localStorage.removeItem(storageKey);
    } catch (err) { setError(err?.userMessage || "We couldn't save your answers. Your work is still here. Try again."); }
    finally { setBusy(false); }
  }
  async function retry() {
    setBusy(true);
    setError("");
    try {
      const res = await startV2AssessmentAttempt(moduleKey, assessmentKey, { suppressToast: true });
      setData(res.data);
      setResult(null);
      setAnswers({});
      setIndex(0);
      setConfirmSubmit(false);
    } catch (err) { setError(err?.userMessage || "A new attempt could not be started."); }
    finally { setBusy(false); }
  }
  if (error && !data) return <V2Error message={error} onRetry={load} moduleRoute={stageRoute} />;
  if (!data) return <V2Loading text="Loading questions..." />;
  const breadcrumb = <nav aria-label="Breadcrumb" className="text-sm"><Link to="/learning-v2">My Course</Link><span aria-hidden="true"> / </span><Link to={stageRoute}>Stage</Link><span aria-hidden="true"> / </span><span aria-current="page">{data.assessment.title}</span></nav>;
  if (result) {
    const pending = result.grading_state === "pending";
    const outcome = pending ? "Grading pending" : result.passed ? "Passed" : "Not quite";
    return <PageContainer width="reading" className="space-y-7">
      <PageHeader breadcrumb={breadcrumb} eyebrow="Checkpoint" title={data.assessment.title} />
      <section className={`learning-feedback ${pending ? "" : result.passed ? "learning-feedback-correct" : "learning-feedback-retry"}`} role="status" aria-labelledby="assessment-outcome">
        <h2 id="assessment-outcome" className="learning-section-title">{outcome}</h2>
        <p className="mt-2">{result.score == null ? "Your answers were saved. Grading is still in progress; you do not need to submit again." : `Score: ${result.score}% · Pass mark: ${result.pass_percent}%`}</p>
        <p className="mt-2 type-meta">{pending ? "You can continue another available activity while grading finishes." : result.passed ? "Your checkpoint is complete. Follow the next course action below." : "Review the feedback, then start a new attempt when you are ready."}</p>
      </section>
      {result.results?.length ? <section aria-labelledby="answer-review-title"><h2 id="answer-review-title" className="learning-section-title">Answer review</h2><ol className="mt-3 divide-y divide-[var(--nexus-border)]">{result.results.map((item) => <li className="py-4" key={item.question_id}><p className="font-semibold">{item.question_text}</p><p className="mt-2 font-semibold">{item.grading_status === "needs_review" ? "Waiting for grading" : item.is_correct ? "Correct" : "Not quite"}</p>{item.correct_answer ? <p className="type-meta mt-2">Correct answer: {item.correct_answer.join(", ")}</p> : null}{item.explanation ? <p className="mt-2">{item.explanation}</p> : null}</li>)}</ol></section> : null}
      {error ? <p role="alert" className="notice-error rounded-lg p-3">{error}</p> : null}
      <div className="flex flex-wrap gap-3">{result.passed ? <V2NextStep moduleKey={moduleKey} /> : pending ? <Link className="btn-primary" to={stageRoute}>Back to Stage</Link> : <button className="btn-primary" disabled={busy} onClick={retry} type="button">{busy ? "Starting..." : "Try again"}</button>}{!pending && <Link className="btn-quiet" to={stageRoute}>Back to Stage</Link>}</div>
    </PageContainer>;
  }
  const question = data.questions[index];
  if (!question) return <V2Error title="No questions available" message="This knowledge check has not been configured yet." />;
  const answer = answers[question.id];
  const isText = ["short_answer", "free_response"].includes(question.type);
  return <PageContainer width="reading" className="space-y-7">
    <PageHeader breadcrumb={breadcrumb} eyebrow={data.assessment.role === "module_quiz" ? "Module Quiz" : "Quick Check"} title={data.assessment.title} description="Answer the questions, then check the server result. You can review your answers before submitting." />
    {error ? <p className="notice-error rounded-lg p-3" role="alert">{error}</p> : null}
    <nav aria-label="Question navigator" className="flex flex-wrap gap-2">{data.questions.map((item, questionIndex) => {
      const isAnswered = answered(answers[item.id]);
      const current = questionIndex === index;
      return <button aria-current={current ? "step" : undefined} aria-label={`Question ${questionIndex + 1}: ${isAnswered ? "answered" : "unanswered"}${current ? ", current" : ""}`} className={`learning-question-nav ${current ? "learning-question-nav-current" : ""}`} key={item.id} onClick={() => { setIndex(questionIndex); setConfirmSubmit(false); }} type="button">{questionIndex + 1}</button>;
    })}</nav>
    <section aria-labelledby="checkpoint-question-title" className="learning-section">
      <p className="type-label">Question {index + 1} of {data.questions.length}</p>
      <h2 id="checkpoint-question-title" className="learning-section-title mt-2">{question.question_text}</h2>
      {isText ? <div className="mt-5"><label className="mb-2 block font-semibold" htmlFor={`answer-${question.id}`}>Your answer</label>{question.type === "free_response" ? <textarea id={`answer-${question.id}`} className="input-field min-h-40 w-full" value={answer || ""} onChange={(event) => update(question, event.target.value)} /> : <input id={`answer-${question.id}`} className="input-field w-full" value={answer || ""} onChange={(event) => update(question, event.target.value)} autoComplete="off" />}</div>
        : <fieldset className="mt-5 space-y-2" aria-describedby="checkpoint-question-title"><legend className="mb-3 font-medium">{question.is_multi_select ? "Select all that apply" : "Choose one answer"}</legend>{question.options.map((option) => {
          const selected = question.is_multi_select ? (Array.isArray(answer) && answer.includes(option.key)) : answer === option.key;
          return <label className={`learning-choice ${selected ? "learning-choice-selected" : ""}`} key={option.key}><input type={question.is_multi_select ? "checkbox" : "radio"} name={`question-${question.id}`} checked={selected} onChange={() => question.is_multi_select ? toggle(question, option.key) : update(question, option.key)} /><span><strong>{option.key}.</strong> {option.text}</span></label>;
        })}</fieldset>}
    </section>
    {confirmSubmit ? <section className="learning-feedback learning-feedback-retry" role="alert"><p className="font-semibold">You still have {unansweredIndexes.length} unanswered question{unansweredIndexes.length === 1 ? "" : "s"}.</p><div className="mt-3 flex flex-wrap gap-2"><button className="btn-primary" onClick={() => { setIndex(unansweredIndexes[0]); setConfirmSubmit(false); }} type="button">Review unanswered</button><button className="btn-quiet" disabled={busy} onClick={submit} type="button">Submit anyway</button></div></section> : null}
    {!confirmSubmit ? <div className="flex flex-wrap gap-3">{index > 0 ? <button className="btn-secondary" onClick={() => setIndex((value) => value - 1)} type="button">Previous question</button> : null}{index < data.questions.length - 1 ? <button className="btn-primary" onClick={() => setIndex((value) => value + 1)} type="button">Next question</button> : <button className="btn-primary" disabled={busy} onClick={requestSubmit} type="button">{busy ? "Submitting..." : "Submit answers"}</button>}</div> : null}
  </PageContainer>;
}
