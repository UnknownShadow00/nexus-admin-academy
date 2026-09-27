"use strict";

function ChoiceField({ choices, value, onChange, name = "choice" }) {
  return <fieldset className="space-y-2">
    <legend className="sr-only">Choose one answer</legend>
    {choices.map((choice) => <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-3 focus-within:ring-2 focus-within:ring-teal-600 dark:border-slate-700" key={choice.id}>
      <input className="mt-1 accent-teal-700" type="radio" name={name} value={choice.id} checked={value === choice.id} onChange={() => onChange(choice.id)} required />
      <span>{choice.label}</span>
    </label>)}
  </fieldset>;
}

export function MatchingInteraction({ content, value = {}, onChange }) {
  return <div className="space-y-4">{content.left.map((item) => <div className="grid gap-2 sm:grid-cols-2 sm:items-center" key={item.id}>
    <label className="font-medium" htmlFor={`match-${item.id}`}>{item.text}</label>
    <select className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-600 dark:bg-slate-900" id={`match-${item.id}`} value={value[item.id] || ""} onChange={(event) => onChange({ ...value, [item.id]: event.target.value })} required>
      <option value="">Choose a match</option>
      {content.right.map((right) => <option key={right.id} value={right.id}>{right.text}</option>)}
    </select>
  </div>)}</div>;
}

export function ImageIdentifyInteraction({ content, value, onChange }) {
  return <div className="space-y-4">
    <img className="max-h-64 w-full rounded-lg bg-slate-50 object-contain dark:bg-slate-900" src={content.image_url} alt={content.image_alt} />
    <p className="font-medium">{content.question}</p>
    <ChoiceField choices={content.choices} value={value} onChange={onChange} />
  </div>;
}

export function OrderingInteraction({ content, value, onChange }) {
  const items = value?.length ? value : content.steps.map((step) => step.id);
  const labels = Object.fromEntries(content.steps.map((step) => [step.id, step.text]));
  function move(index, direction) {
    const next = [...items];
    [next[index], next[index + direction]] = [next[index + direction], next[index]];
    onChange(next);
  }
  return <ol className="space-y-2" aria-label="Steps in your chosen order">{items.map((id, index) => <li className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700" key={id}>
    <span className="w-6 shrink-0 font-semibold">{index + 1}.</span>
    <span className="flex-1">{labels[id]}</span>
    <button className="btn-secondary min-h-10 px-3 focus-visible:ring-2 focus-visible:ring-teal-600" type="button" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Move ${labels[id]} up`}>Move up</button>
    <button className="btn-secondary min-h-10 px-3 focus-visible:ring-2 focus-visible:ring-teal-600" type="button" disabled={index === items.length - 1} onClick={() => move(index, 1)} aria-label={`Move ${labels[id]} down`}>Move down</button>
  </li>)}</ol>;
}

export function CommandOutputInteraction({ content, value, onChange }) {
  return <div className="space-y-4">
    <div><p className="text-sm font-semibold">Command</p><code className="block rounded-lg bg-slate-100 p-3 dark:bg-slate-900">{content.command}</code></div>
    <div><p className="text-sm font-semibold">Output</p><pre className="overflow-x-auto rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-900">{content.output}</pre></div>
    <p className="font-medium">{content.question}</p>
    <ChoiceField choices={content.choices} value={value} onChange={onChange} />
  </div>;
}

export function TypedAnswerInteraction({ content, value, onChange }) {
  return <div className="space-y-2"><label className="block font-medium" htmlFor="interaction-answer">{content.question}</label>
    <input className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-600 dark:bg-slate-900" id="interaction-answer" type="text" maxLength={500} autoComplete="off" value={value || ""} onChange={(event) => onChange(event.target.value)} required />
  </div>;
}

export function SafeActionInteraction({ content, value, onChange }) {
  return <div className="space-y-4"><p className="font-medium">{content.scenario}</p>
    {content.safety_critical ? <p className="text-sm text-amber-800 dark:text-amber-300">Choose the safest next step.</p> : null}
    <ChoiceField choices={content.choices} value={value} onChange={onChange} />
  </div>;
}

export const interactionRenderers = {
  matching: MatchingInteraction,
  image_identification: ImageIdentifyInteraction,
  ordering: OrderingInteraction,
  command_output: CommandOutputInteraction,
  typed_answer: TypedAnswerInteraction,
  safe_action: SafeActionInteraction,
};
