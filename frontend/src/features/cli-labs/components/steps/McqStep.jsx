export default function McqStep({ step, decision = false, onCorrect }) {
  function choose(index) {
    if (index === step.correctIndex) {
      onCorrect();
      return;
    }
    onCorrect(false);
  }

  return (
    <div className="space-y-4">
      <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{step.question}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {(step.options || []).map((option, index) => (
          <button
            key={`${option}-${index}`}
            type="button"
            onClick={() => choose(index)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm font-medium text-slate-700 transition hover:border-cyan-300 hover:bg-cyan-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:border-cyan-600 dark:hover:bg-cyan-950/30"
          >
            {decision ? <span className="mr-2 text-xs uppercase text-cyan-700 dark:text-cyan-300">Decision</span> : null}
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
