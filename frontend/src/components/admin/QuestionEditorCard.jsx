import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Plus, X } from "lucide-react";
import { updateQuestion, validateQuestionDraft } from "../../services/api";

const LETTERS = ["a", "b", "c", "d", "e", "f", "g", "h"];
const REQUIRED_LETTERS = new Set(["a", "b", "c", "d"]); // option_a-d are NOT NULL in the schema

function initialOptions(question) {
  return LETTERS.filter((letter) => (question[`option_${letter}`] || "").trim() || REQUIRED_LETTERS.has(letter)).map(
    (letter) => ({ letter, text: question[`option_${letter}`] || "" })
  );
}

function initialCorrectSet(question) {
  const raw = question.correct_answers || question.correct_answer || "";
  return new Set(
    String(raw)
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
  );
}

export default function QuestionEditorCard({ question, index, onSaved }) {
  const [options, setOptions] = useState(() => initialOptions(question));
  const [questionText, setQuestionText] = useState(question.question_text);
  const [explanation, setExplanation] = useState(question.explanation || "");
  const [correctSet, setCorrectSet] = useState(() => initialCorrectSet(question));
  const [validation, setValidation] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const nextAddableLetter = LETTERS.find((letter) => !options.some((o) => o.letter === letter));
  const isMulti = correctSet.size > 1;

  const draftPayload = useMemo(
    () => ({
      question_text: questionText,
      options: options.map((o) => o.text),
      correct_answers: Array.from(correctSet),
      explanation,
    }),
    [questionText, options, correctSet, explanation]
  );

  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      try {
        const res = await validateQuestionDraft(draftPayload, { suppressToast: true });
        if (active) setValidation(res.data);
      } catch {
        if (active) setValidation(null);
      }
    }, 300);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [draftPayload]);

  const updateOptionText = (letter, text) => {
    setOptions((current) => current.map((o) => (o.letter === letter ? { ...o, text } : o)));
  };

  const addOption = () => {
    if (!nextAddableLetter) return;
    setOptions((current) => [...current, { letter: nextAddableLetter, text: "" }]);
  };

  const removeOption = (letter) => {
    if (REQUIRED_LETTERS.has(letter)) return;
    setOptions((current) => current.filter((o) => o.letter !== letter));
    setCorrectSet((current) => {
      const next = new Set(current);
      next.delete(letter.toUpperCase());
      return next;
    });
  };

  const toggleCorrect = (letter) => {
    const upper = letter.toUpperCase();
    setCorrectSet((current) => {
      const next = new Set(current);
      if (next.has(upper)) {
        if (next.size === 1) return next; // must keep at least one correct answer
        next.delete(upper);
      } else {
        next.add(upper);
      }
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      const sortedCorrect = Array.from(correctSet).sort();
      const patch = { question_text: questionText, explanation };
      LETTERS.forEach((letter) => {
        const found = options.find((o) => o.letter === letter);
        patch[`option_${letter}`] = found ? found.text : REQUIRED_LETTERS.has(letter) ? "" : null;
      });
      patch.correct_answer = sortedCorrect[0] || "A";
      patch.correct_answers = sortedCorrect.length > 1 ? sortedCorrect.join(",") : "";
      const res = await updateQuestion(question.id, patch, { suppressToast: true });
      onSaved?.(question.id, { ...patch, flagged_for_review: !res.data?.valid });
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setSaving(false);
    }
  };

  const visibleOptions = options.filter((o) => o.text.trim());

  return (
    <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-slate-900 dark:text-slate-100">Question {index + 1}</p>
        {question.flagged_for_review ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle size={12} aria-hidden="true" />
            Flagged for review
          </span>
        ) : null}
      </div>
      {question.flagged_for_review && question.flag_reason ? (
        <p className="text-xs text-amber-700 dark:text-amber-400">{question.flag_reason}</p>
      ) : null}

      <label className="block text-sm">
        Question text
        <textarea
          className="input-field mt-1 w-full"
          rows={2}
          value={questionText}
          onChange={(e) => setQuestionText(e.target.value)}
        />
      </label>

      {isMulti ? (
        <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">
          Students must select all correct answers and no incorrect answers.
        </p>
      ) : null}

      <div className="space-y-2">
        {options.map((option) => (
          <div key={option.letter} className="flex items-center gap-2">
            <input
              type="checkbox"
              aria-label={`Option ${option.letter.toUpperCase()} is correct`}
              checked={correctSet.has(option.letter.toUpperCase())}
              onChange={() => toggleCorrect(option.letter)}
            />
            <span className="w-5 shrink-0 text-sm font-bold uppercase text-slate-500">{option.letter}</span>
            <input
              className="input-field flex-1"
              placeholder={`Option ${option.letter.toUpperCase()} text`}
              value={option.text}
              onChange={(e) => updateOptionText(option.letter, e.target.value)}
            />
            {!REQUIRED_LETTERS.has(option.letter) ? (
              <button
                type="button"
                aria-label={`Remove option ${option.letter.toUpperCase()}`}
                className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600 dark:hover:bg-slate-800"
                onClick={() => removeOption(option.letter)}
              >
                <X size={16} aria-hidden="true" />
              </button>
            ) : (
              <span className="w-6" />
            )}
          </div>
        ))}
        {nextAddableLetter ? (
          <button type="button" className="btn-secondary text-sm" onClick={addOption}>
            <Plus size={14} className="mr-1 inline" aria-hidden="true" />
            Add option
          </button>
        ) : null}
      </div>

      <label className="block text-sm">
        Explanation
        <input
          className="input-field mt-1 w-full"
          placeholder="Explanation (shown after the student answers)"
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
        />
      </label>

      {validation && !validation.valid ? (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
          {validation.errors.map((err) => (
            <div key={err.message}>{err.message}</div>
          ))}
        </div>
      ) : null}
      {validation?.warnings?.length ? (
        <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          {validation.warnings.map((w) => (
            <div key={w.message}>{w.message}</div>
          ))}
        </div>
      ) : null}

      <div className="rounded border border-dashed border-slate-300 p-3 dark:border-slate-700">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Student preview</p>
        <p className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-200">{questionText}</p>
        <div className="space-y-1">
          {visibleOptions.map((option, i) => (
            <div key={option.letter} className="rounded border border-slate-200 px-2 py-1 text-sm dark:border-slate-700">
              <span className="font-semibold">{String.fromCharCode(65 + i)}.</span> {option.text}
            </div>
          ))}
        </div>
      </div>

      <button type="button" className="btn-primary" onClick={save} disabled={saving}>
        {saving ? "Saving..." : saved ? "Saved" : "Save"}
      </button>
    </div>
  );
}
