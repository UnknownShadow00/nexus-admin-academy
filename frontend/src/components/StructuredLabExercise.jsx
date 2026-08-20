import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import HardwareIdentificationVisual from "./HardwareIdentificationVisual";
import TerminalWidget from "./Terminal";

function isSelected(answers, questionId, optionId) {
  return (answers[questionId] || []).includes(optionId);
}

function toggleAnswer(answers, question, optionId) {
  const current = answers[question.id] || [];
  if (question.type === "multi_choice") {
    const next = current.includes(optionId) ? current.filter((id) => id !== optionId) : [...current, optionId];
    return { ...answers, [question.id]: next };
  }
  return { ...answers, [question.id]: [optionId] };
}

export default function StructuredLabExercise({ questions, requiredCommands = [], feedback, submitted, busy, onSubmit }) {
  const [answers, setAnswers] = useState({});
  const [prefillCommand, setPrefillCommand] = useState("");
  const [terminalSession, setTerminalSession] = useState("");

  const list = Array.isArray(questions) ? questions : [];
  const commands = Array.isArray(requiredCommands) ? requiredCommands : [];
  const feedbackById = new Map((feedback?.questions || []).map((item) => [item.id, item]));
  const allAnswered = list.every((question) => (answers[question.id] || []).length > 0);
  const normalizedSession = terminalSession.toLowerCase().replaceAll(/\s+/g, " ");
  const commandWasRun = (command) => normalizedSession.includes(command.toLowerCase().replaceAll(/\s+/g, " "));
  const allCommandsRun = commands.every(commandWasRun);

  return (
    <div className="space-y-4">
      {feedback ? (
        <div
          className={`rounded-lg border px-4 py-3 text-sm font-medium ${
            feedback.score_pct >= 70
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"
              : "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300"
          }`}
        >
          Score: {feedback.score_pct}% correct
        </div>
      ) : null}

      {commands.length ? (
        <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-900 dark:bg-blue-950/20">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Use the practice terminal first</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Run each command and read its output. Then use that evidence to answer the diagnostic questions.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {commands.map((command) => (
              <button
                key={command}
                type="button"
                className={commandWasRun(command) ? "btn-secondary border-emerald-500 text-emerald-700" : "btn-secondary"}
                disabled={submitted || busy}
                onClick={() => setPrefillCommand(command)}
              >
                {commandWasRun(command) ? "✓ " : "Try "}<code>{command}</code>
              </button>
            ))}
          </div>
          <TerminalWidget prefillCommand={prefillCommand} onSessionChange={setTerminalSession} />
        </div>
      ) : null}

      {list.map((question, index) => {
        const result = feedbackById.get(question.id);
        return (
          <fieldset
            key={question.id}
            className="rounded-lg border border-slate-200 p-4 dark:border-slate-700"
            disabled={submitted || busy}
          >
            <legend className="px-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              {index + 1}. {question.prompt}
            </legend>
            {question.visualId ? <HardwareIdentificationVisual visualId={question.visualId} /> : null}
            {question.context ? (
              <pre className="mt-2 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
                {question.context}
              </pre>
            ) : null}
            <div className="mt-3 space-y-2">
              {(question.options || []).map((option) => (
                <label
                  key={option.id}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  <input
                    type={question.type === "multi_choice" ? "checkbox" : "radio"}
                    name={question.id}
                    checked={isSelected(answers, question.id, option.id)}
                    onChange={() => setAnswers((prev) => toggleAnswer(prev, question, option.id))}
                    className="h-4 w-4"
                  />
                  {option.label}
                </label>
              ))}
            </div>
            {result ? (
              <div
                className={`mt-3 flex items-start gap-2 rounded-md px-3 py-2 text-xs ${
                  result.correct
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
                    : "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300"
                }`}
              >
                {result.correct ? (
                  <CheckCircle2 size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                ) : (
                  <XCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                )}
                <span>{result.explanation}</span>
              </div>
            ) : null}
          </fieldset>
        );
      })}

      {!submitted ? (
        <button
          type="button"
          className="btn-primary"
          disabled={!allAnswered || !allCommandsRun || busy}
          onClick={() => onSubmit(answers, terminalSession)}
        >
          {busy ? "Submitting..." : feedback ? "Try Again" : "Submit Answers"}
        </button>
      ) : null}
    </div>
  );
}
