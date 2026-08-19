import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import HardwareIdentificationVisual from "./HardwareIdentificationVisual";

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

export default function StructuredLabExercise({ questions, feedback, submitted, busy, onSubmit }) {
  const [answers, setAnswers] = useState({});

  const list = Array.isArray(questions) ? questions : [];
  const feedbackById = new Map((feedback?.questions || []).map((item) => [item.id, item]));
  const allAnswered = list.every((question) => (answers[question.id] || []).length > 0);

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
          disabled={!allAnswered || busy}
          onClick={() => onSubmit(answers)}
        >
          {busy ? "Submitting..." : feedback ? "Try Again" : "Submit Answers"}
        </button>
      ) : null}
    </div>
  );
}
