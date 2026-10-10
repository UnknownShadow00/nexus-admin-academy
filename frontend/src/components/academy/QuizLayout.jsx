import { ArrowLeft, ArrowRight, CheckSquare, Flag, Lightbulb } from "lucide-react";
import { useState } from "react";
import AcademyScene from "./AcademyScene";
import "./quiz.css";

export function QuizFrame({ children }) {
  return <main className="academy-quiz">
    <div className="quiz-backdrop" aria-hidden="true"><img className="quiz-day" src="/academy/castle-day-refined.webp" alt="" /><img className="quiz-night" src="/academy/castle-night-refined.webp" alt="" /><div /></div>
    {children}
  </main>;
}

// Position, answered count and server outcome deliberately have separate labels.
export default function QuizLayout({ title, numbered = false, eyebrow = "Knowledge check", questions, index, hasAnswer, onNavigate, onSubmit, busy, storage, back, children, headingRef, instruction, nextLabel, submitLabel = "Submit answers", error }) {
  const [flags, setFlags] = useState([]);
  const [review, setReview] = useState(false);
  const answered = questions.filter(hasAnswer).length;
  const total = questions.length;
  const unanswered = questions.map((q, i) => hasAnswer(q) ? null : i).filter(i => i !== null);
  const flagged = flags.includes(index);
  function navigate(i) { setReview(false); onNavigate(i); }
  return <QuizFrame>
    <header className="card quiz-header">
      <div className="quiz-heading"><div className="heading-with-icon"><span className="tile violet"><CheckSquare size={20} aria-hidden="true" /></span><div><p className="eyebrow purple">{eyebrow}</p><h1 id="quiz-title">{title}</h1></div></div><div className="lesson-meta"><span className="small sub">Current question <b>{index + 1}</b> of {total}</span><span className="chip violet">{answered} answered · {Math.round(answered / total * 100)}% answered</span></div></div>
      <div className="progress-line quiz-completion"><div className="bar" role="progressbar" aria-label="Questions answered" aria-valuemin={0} aria-valuemax={total} aria-valuenow={answered}><span style={{ width: `${answered / total * 100}%`, background: "var(--purple)" }} /></div><span className="small sub">{answered} of {total} answered</span></div>
    </header>
    <div className="activity-layout"><article className="stack">
      <section className="card question-card" aria-busy={busy}>
        <div className="question-title"><span className="question-id mono" aria-hidden="true">Q{index + 1}</span><div><p className="small muted">Question {index + 1} of {total}</p><h2 ref={headingRef} tabIndex={-1} id="checkpoint-question-title">{numbered ? `${index + 1}. ` : ""}{questions[index].question_text}</h2></div></div>
        {children}
        <div className="callout amber"><Lightbulb size={24} aria-hidden="true" /><p><strong>Think it through</strong><br />{instruction || "Read each option carefully. You can revise your answers before submitting."}</p></div>
        {error ? <p role="alert" className="notice-error rounded-lg p-3">{error}</p> : null}
        {review ? <section className="quiz-submit-review" aria-label="Review before submission"><h3>Review your answers</h3><p>{unanswered.length ? `You still have ${unanswered.length} unanswered question${unanswered.length === 1 ? "" : "s"}.` : "Every question has an answer. Your result is determined by server grading after submission."}</p><div className="actions">{unanswered.length ? <button className="btn btn-secondary" type="button" onClick={() => navigate(unanswered[0])} disabled={busy}>Review unanswered</button> : null}<button className="btn btn-primary" type="button" disabled={busy} onClick={onSubmit}>{busy ? "Submitting..." : submitLabel}</button><button className="btn btn-secondary" type="button" disabled={busy} onClick={() => setReview(false)}>Keep editing</button></div></section> : null}
        <div className="question-actions"><button type="button" className="btn btn-secondary" disabled={busy || index === 0} onClick={() => navigate(index - 1)}><ArrowLeft size={17} aria-hidden="true" />Previous</button><div className="actions"><button className="btn btn-ghost" type="button" disabled={busy} aria-pressed={flagged} onClick={() => setFlags(previous => flagged ? previous.filter(i => i !== index) : [...previous, index])}><Flag size={17} aria-hidden="true" />{flagged ? "Flagged for review" : "Flag for review"}</button>{index < total - 1 ? <button type="button" className="btn btn-primary" disabled={busy} onClick={() => navigate(index + 1)}>{nextLabel || "Next question"}<ArrowRight size={17} aria-hidden="true" /></button> : <button type="button" className="btn btn-primary" disabled={busy} onClick={onSubmit}>{busy ? "Submitting..." : submitLabel}</button>}</div></div>
        <p className="small muted" role="status">{storage}</p>
      </section>
    </article><aside className="stack quiz-rail" aria-label="Your attempt">
      <section className="card attempt"><div className="section-title"><h2>Your attempt</h2><span className="mono muted small" aria-live="polite">{answered} answered</span></div><nav className="question-grid" aria-label="Question navigator">{questions.map((q, i) => <button key={q.id} type="button" disabled={busy} className={`${i === index ? "current" : flags.includes(i) ? "flagged" : hasAnswer(q) ? "answered" : ""}`} aria-current={i === index ? "step" : undefined} aria-label={`Go to question ${i + 1}, ${hasAnswer(q) ? "answered" : "unanswered"}${flags.includes(i) ? ", flagged" : ""}`} onClick={() => navigate(i)}>{i + 1}</button>)}</nav><div className="legend"><span><i className="current" />Current</span><span><i className="answered" />Answered</span><span><i className="flagged" />Flagged</span></div><div className="attempt-footer"><button className="btn btn-secondary" type="button" disabled={busy} onClick={() => setReview(true)}>Review and submit</button><p className="muted small">Change answers until you submit. Flags are reminders for this visit.</p></div></section>
      <section className="quote"><AcademyScene kind="quote" dark /><div className="quote-content"><p className="eyebrow">KEEP LEARNING</p><p>Review the material. Take your time. A saved answer is not a passing grade.</p>{back}</div></section>
    </aside></div>
  </QuizFrame>;
}
