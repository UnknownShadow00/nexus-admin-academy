import { useState } from "react";

const BAD_NOTE = "user pc broken, fixed it, closing.";

const VAGUE_WORDS = ["fixed", "broken", "probably", "stuff", "thing", "seems ok", "everything"];

const FIELDS = [
  { key: "summary", label: "Issue summary", placeholder: "What did the user report? (one line)" },
  { key: "troubleshooting", label: "Troubleshooting performed", placeholder: "What did you check or run? (one line)" },
  { key: "resolution", label: "Resolution", placeholder: "What did you change? (one line)" },
  { key: "verification", label: "User confirmation / verification", placeholder: "How do you know it's fixed, and did the user confirm?" },
];

function evaluateField(key, value) {
  const trimmed = value.trim();
  if (!trimmed) return { ok: false, message: "Not filled in yet." };
  const lower = trimmed.toLowerCase();
  const vague = VAGUE_WORDS.find((word) => lower.includes(word));
  if (vague) return { ok: false, message: `Too vague — "${vague}" doesn't tell a stranger what actually happened. Be specific.` };
  if (trimmed.length < 8) return { ok: false, message: "Too short to be useful to the next technician. Add a concrete detail." };
  if (key === "verification" && !/(confirm|verif|test|check|showed|ping|worked|resolved)/i.test(trimmed)) {
    return { ok: false, message: "This should state how you verified the fix, not just that you made a change." };
  }
  return { ok: true, message: "Good — specific and actionable." };
}

export default function TicketNoteExercise() {
  const [values, setValues] = useState({ summary: "", troubleshooting: "", resolution: "", verification: "" });
  const [checked, setChecked] = useState(false);

  const results = FIELDS.reduce((acc, field) => {
    acc[field.key] = evaluateField(field.key, values[field.key]);
    return acc;
  }, {});
  const allGood = checked && FIELDS.every((field) => results[field.key].ok);

  return (
    <section className="panel space-y-4" aria-labelledby="ticket-note-exercise">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">Guided practice</p>
        <h2 className="mt-1 text-xl font-bold" id="ticket-note-exercise">Rewrite this bad ticket note</h2>
      </div>
      <blockquote className="rounded-lg border-l-4 border-amber-400 bg-amber-50 p-3 text-sm italic text-amber-900 dark:border-amber-600 dark:bg-amber-950/20 dark:text-amber-100">
        "{BAD_NOTE}"
      </blockquote>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Fill in each part of a proper internal note. Keep each line short and specific — this is not an essay.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {FIELDS.map((field) => (
          <label key={field.key} className="block text-sm">
            <span className="font-semibold text-slate-800 dark:text-slate-200">{field.label}</span>
            <input
              className="input-field mt-1 w-full"
              onChange={(event) => { setValues((prev) => ({ ...prev, [field.key]: event.target.value })); setChecked(false); }}
              placeholder={field.placeholder}
              value={values[field.key]}
            />
            {checked ? (
              <span className={`mt-1 block text-xs font-medium ${results[field.key].ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
                {results[field.key].ok ? "✓ " : "✗ "}{results[field.key].message}
              </span>
            ) : null}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-secondary" onClick={() => setChecked(true)} type="button">Check my note</button>
        {allGood ? (
          <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
            ✓ This note keeps internal detail separate from vague claims — a stranger could pick this up.
          </span>
        ) : checked ? (
          <span className="text-sm font-semibold text-amber-700 dark:text-amber-300">Fix the flagged fields above and check again.</span>
        ) : null}
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        This exercise is a study aid — it does not affect lesson completion or your score.
      </p>
    </section>
  );
}
