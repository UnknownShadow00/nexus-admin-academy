import { RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

function shuffledFields(fields) {
  return fields
    .map((label, index) => ({ label, index }))
    .sort((a, b) => a.label.localeCompare(b.label) || a.index - b.index);
}

export default function FrameBuilderStep({ step, onCorrect }) {
  const fields = useMemo(() => shuffledFields(step.fields || []), [step.fields]);
  const [selected, setSelected] = useState([]);

  function choose(field) {
    if (selected.includes(field.index)) return;
    setSelected((current) => [...current, field.index]);
  }

  function reset() {
    setSelected([]);
  }

  function check() {
    const expected = step.correctOrder || [];
    const correct = selected.length === expected.length && selected.every((fieldIndex, index) => fieldIndex === expected[index]);
    onCorrect(correct || false);
  }

  return (
    <div className="space-y-4">
      <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{step.question}</p>
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950">
        <div className="flex min-h-12 flex-wrap items-center gap-2">
          {selected.length ? (
            selected.map((fieldIndex, index) => (
              <span key={`${fieldIndex}-${index}`} className="rounded-md bg-cyan-100 px-3 py-1.5 text-sm font-medium text-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200">
                {step.fields[fieldIndex]}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-500 dark:text-slate-400">Select fields in frame order.</span>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {fields.map((field) => {
          const placed = selected.includes(field.index);
          return (
            <button
              key={field.index}
              type="button"
              onClick={() => choose(field)}
              disabled={placed}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-cyan-300 hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-45 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:border-cyan-600 dark:hover:bg-cyan-950/30"
            >
              {field.label}
            </button>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" type="button" onClick={check} disabled={selected.length !== (step.fields || []).length}>
          Check frame
        </button>
        <button className="btn-secondary gap-2" type="button" onClick={reset}>
          <RotateCcw size={16} />
          Reset
        </button>
      </div>
    </div>
  );
}
