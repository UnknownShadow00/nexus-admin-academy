import { useState } from "react";

function acceptedAnswers(step) {
  const answers = step.accept?.length ? step.accept : [step.answer];
  return answers.map((answer) => String(answer || "").trim().toLowerCase());
}

export default function HexInputStep({ step, onCorrect }) {
  const [value, setValue] = useState("");

  function submit(event) {
    event.preventDefault();
    const normalized = value.trim().toLowerCase();
    if (acceptedAnswers(step).includes(normalized)) {
      onCorrect();
      return;
    }
    onCorrect(false);
  }

  return (
    <form className="space-y-3" onSubmit={submit}>
      <label className="block text-sm leading-6 text-slate-700 dark:text-slate-200" htmlFor={`hex-${step.id}`}>
        {step.question}
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={`hex-${step.id}`}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="min-h-10 rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm text-slate-800 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-cyan-500 dark:focus:ring-cyan-950"
          autoComplete="off"
          spellCheck="false"
        />
        <button className="btn-primary justify-center" type="submit">
          Check
        </button>
      </div>
    </form>
  );
}
