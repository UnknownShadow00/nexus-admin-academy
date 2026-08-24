import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, Eye, ShieldCheck, XCircle } from "lucide-react";

function selected(answers, questionId, optionId) {
  return (answers[questionId] || []).includes(optionId);
}

function updateAnswer(answers, question, optionId) {
  const current = answers[question.id] || [];
  if (question.type === "multi_choice") {
    const next = current.includes(optionId) ? current.filter((id) => id !== optionId) : [...current, optionId];
    return { ...answers, [question.id]: next };
  }
  return { ...answers, [question.id]: [optionId] };
}

const NOTE_FIELDS = [
  ["issue", "Issue", "State the support issue in one sentence."],
  ["evidence", "Evidence", "Name the evidence that supports your diagnosis."],
  ["action", "Action", "Record the safe action you chose."],
  ["verification", "Verification", "Record what proves the expected outcome."],
];

export default function EndpointEvidenceWorkbench({ workbench, questions, feedback, submitted, busy, onVerify, onSubmit }) {
  const panels = Array.isArray(workbench?.panels) ? workbench.panels : [];
  const requiredInspections = Array.isArray(workbench?.required_inspections) ? workbench.required_inspections : [];
  const list = Array.isArray(questions) ? questions : [];
  const [opened, setOpened] = useState([]);
  const [activePanel, setActivePanel] = useState(null);
  const [answers, setAnswers] = useState({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [verificationOpened, setVerificationOpened] = useState(false);
  const [verificationMessage, setVerificationMessage] = useState("");
  const [notes, setNotes] = useState({ issue: "", evidence: "", action: "", verification: "" });

  const feedbackById = useMemo(
    () => new Map((feedback?.questions || []).map((item) => [item.id, item])),
    [feedback],
  );
  const inspectionsComplete = requiredInspections.every((panelId) => opened.includes(panelId));
  const currentQuestion = list[questionIndex];
  const currentAnswered = currentQuestion && (answers[currentQuestion.id] || []).length > 0;
  const decisionsComplete = list.length > 0 && list.every((question) => (answers[question.id] || []).length > 0);
  const documentationComplete = NOTE_FIELDS.every(([field]) => notes[field].trim().length > 0);

  function openPanel(panelId) {
    setActivePanel(panelId);
    setOpened((current) => (current.includes(panelId) ? current : [...current, panelId]));
  }

  function continueDecision() {
    if (!currentAnswered) return;
    setQuestionIndex((index) => Math.min(index + 1, list.length - 1));
  }

  function chooseAnswer(question, optionId) {
    setAnswers((current) => updateAnswer(current, question, optionId));
    setVerificationOpened(false);
    setVerificationMessage("");
  }

  async function verifyPlan() {
    const result = await onVerify(answers);
    setVerificationOpened(Boolean(result?.ready));
    setVerificationMessage(result?.message || "");
  }

  const activeEvidence = panels.find((panel) => panel.id === activePanel);
  const guidanceLabel = workbench?.guidance_level === "practice" ? "Guided practice" : workbench?.guidance_level === "prove" ? "Prove case" : "Troubleshoot case";

  return (
    <section className="min-w-0 space-y-5" aria-labelledby="endpoint-workbench-title">
      <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-900 dark:bg-blue-950/20">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">{guidanceLabel}</p>
        <h3 id="endpoint-workbench-title" className="mt-1 text-base font-semibold text-slate-900 dark:text-white">Endpoint evidence workbench</h3>
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">{workbench?.brief}</p>
        {workbench?.guidance ? (
          <div className="mt-3 rounded-md border border-blue-200 bg-white/70 p-3 text-sm text-slate-700 dark:border-blue-800 dark:bg-slate-950/40 dark:text-slate-300">
            <strong>Investigation hint:</strong> {workbench.guidance}
          </div>
        ) : null}
      </div>

      <div className="min-w-0 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Eye size={17} aria-hidden="true" />
          <h4 className="font-semibold text-slate-900 dark:text-white">1. Inspect evidence</h4>
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Open the records you believe matter. Required investigation: {opened.filter((id) => requiredInspections.includes(id)).length}/{requiredInspections.length}.</p>
        <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Endpoint evidence panels">
          {panels.map((panel) => (
            <button
              key={panel.id}
              type="button"
              role="tab"
              aria-selected={activePanel === panel.id}
              aria-controls={`evidence-${panel.id}`}
              className={`min-h-10 rounded-md border px-3 py-2 text-left text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 ${activePanel === panel.id ? "border-blue-500 bg-blue-50 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200" : "border-slate-200 text-slate-700 dark:border-slate-700 dark:text-slate-300"}`}
              onClick={() => openPanel(panel.id)}
            >
              {opened.includes(panel.id) ? "✓ " : ""}{panel.label}
            </button>
          ))}
        </div>
        {activeEvidence ? (
          <div id={`evidence-${activeEvidence.id}`} role="tabpanel" className="mt-3 min-w-0 rounded-md bg-slate-50 p-3 dark:bg-slate-950">
            <h5 className="text-sm font-semibold text-slate-900 dark:text-white">{activeEvidence.label}</h5>
            <dl className="mt-2 grid min-w-0 gap-2 sm:grid-cols-2">
              {(activeEvidence.fields || []).map((field) => (
                <div key={`${field.label}-${field.value}`} className="min-w-0 rounded border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900">
                  <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{field.label}</dt>
                  <dd className="mt-1 break-words text-sm text-slate-800 dark:text-slate-200">{field.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : (
          <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-950 dark:text-slate-400">Choose a record to inspect. Evidence is not expanded by default.</p>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700" aria-disabled={!inspectionsComplete}>
        <h4 className="font-semibold text-slate-900 dark:text-white">2. Decide and choose a safe action</h4>
        {!inspectionsComplete ? (
          <p className="mt-2 text-sm text-amber-700 dark:text-amber-300" role="status">Inspect the required evidence before making a decision.</p>
        ) : currentQuestion ? (
          <fieldset disabled={submitted || busy} className="mt-3 min-w-0">
            <legend className="text-sm font-semibold text-slate-800 dark:text-slate-200">Decision {questionIndex + 1} of {list.length}: {currentQuestion.prompt}</legend>
            {currentQuestion.context ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{currentQuestion.context}</p> : null}
            <div className="mt-3 grid gap-2">
              {(currentQuestion.options || []).map((option) => (
                <label key={option.id} className="flex min-w-0 cursor-pointer items-start gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  <input
                    className="mt-0.5 h-4 w-4 shrink-0"
                    type={currentQuestion.type === "multi_choice" ? "checkbox" : "radio"}
                    name={currentQuestion.id}
                    checked={selected(answers, currentQuestion.id, option.id)}
                    onChange={() => chooseAnswer(currentQuestion, option.id)}
                  />
                  <span className="min-w-0 break-words">{option.label}</span>
                </label>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {questionIndex > 0 ? <button type="button" className="btn-secondary" onClick={() => setQuestionIndex((index) => index - 1)}>Review previous decision</button> : null}
              {questionIndex < list.length - 1 ? <button type="button" className="btn-secondary" disabled={!currentAnswered} onClick={continueDecision}>Continue investigation</button> : null}
            </div>
          </fieldset>
        ) : null}
        {feedback ? (
          <div className="mt-4 space-y-2" aria-live="polite">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Server-graded result: {feedback.score_pct}%</p>
            {list.map((question) => {
              const result = feedbackById.get(question.id);
              if (!result) return null;
              return (
                <div key={question.id} className={`flex items-start gap-2 rounded-md px-3 py-2 text-xs ${result.correct ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" : "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300"}`}>
                  {result.correct ? <CheckCircle2 size={14} className="mt-0.5 shrink-0" aria-hidden="true" /> : <XCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />}
                  <span>{result.explanation}</span>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <div className="flex items-center gap-2"><ShieldCheck size={17} aria-hidden="true" /><h4 className="font-semibold text-slate-900 dark:text-white">3. Verify the expected outcome</h4></div>
        {!decisionsComplete ? <p className="mt-2 text-sm text-slate-500">Complete every decision before verification becomes available.</p> : !verificationOpened ? (
          <button type="button" className="btn-secondary mt-3" disabled={busy} onClick={verifyPlan}>{busy ? "Checking evidence..." : "Run simulated verification"}</button>
        ) : (
          <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50/60 p-3 dark:border-emerald-900 dark:bg-emerald-950/20" role="status">
            <p className="font-semibold text-emerald-800 dark:text-emerald-200">{workbench?.verification?.label}</p>
            <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-300">{workbench?.verification?.description}</p>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2">
              {(workbench?.verification?.fields || []).map((field) => <div key={`${field.label}-${field.value}`}><dt className="text-xs font-semibold text-emerald-800 dark:text-emerald-200">{field.label}</dt><dd className="break-words text-sm text-emerald-900 dark:text-emerald-100">{field.value}</dd></div>)}
            </dl>
          </div>
        )}
        {verificationMessage ? <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200" role="alert">{verificationMessage}</p> : null}
      </div>

      <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <div className="flex items-center gap-2"><ClipboardCheck size={17} aria-hidden="true" /><h4 className="font-semibold text-slate-900 dark:text-white">4. Document the support conclusion</h4></div>
        <div className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">
          {NOTE_FIELDS.map(([field, label, placeholder]) => (
            <label key={field} className="min-w-0 text-sm font-medium text-slate-700 dark:text-slate-300">{label}
              <textarea className="input-field mt-1 min-h-20 w-full resize-y" value={notes[field]} placeholder={placeholder} disabled={submitted || busy} onChange={(event) => setNotes((current) => ({ ...current, [field]: event.target.value }))} required />
            </label>
          ))}
        </div>
      </div>

      {!submitted ? (
        <button type="button" className="btn-primary w-full sm:w-auto" disabled={!verificationOpened || !documentationComplete || !decisionsComplete || busy} onClick={() => onSubmit(answers, JSON.stringify(notes))}>
          {busy ? "Submitting..." : feedback ? "Submit revised conclusion" : "Submit evidence case"}
        </button>
      ) : null}
    </section>
  );
}
