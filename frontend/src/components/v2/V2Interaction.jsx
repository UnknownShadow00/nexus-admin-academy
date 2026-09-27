import { useCallback, useEffect, useState } from "react";
import { getV2Interaction, submitV2Interaction } from "../../services/api";
import { V2Error, V2Loading } from "./V2PageState";
import V2Status from "./V2Status";
import { interactionRenderers } from "./V2InteractionRenderers";

function initialAnswer(interaction) {
  if (interaction.type === "matching") return {};
  if (interaction.type === "ordering") return interaction.content.steps.map((step) => step.id);
  return "";
}

function responseFor(type, answer) {
  if (type === "matching") return { matches: answer };
  if (type === "ordering") return { order: answer };
  if (type === "typed_answer") return { answer };
  return { choice_id: answer };
}

export default function V2Interaction({ moduleKey, interactionKey }) {
  const [data, setData] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    setError("");
    getV2Interaction(moduleKey, interactionKey, { suppressToast: true }).then((response) => {
      setData(response.data);
      setAnswer(initialAnswer(response.data.interaction));
    }).catch((err) => setError(err?.userMessage || "This interaction could not be loaded."));
  }, [moduleKey, interactionKey]);
  useEffect(load, [load]);
  if (error && !data) return <V2Error title="Interaction unavailable" message={error} onRetry={load} />;
  if (!data) return <V2Loading text="Loading practice..." />;
  const { interaction, progress } = data;
  const Renderer = interactionRenderers[interaction.type];
  if (!Renderer) return <V2Error title="Interaction unavailable" message="This activity type is not supported." />;
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await submitV2Interaction(moduleKey, interactionKey, responseFor(interaction.type, answer), { suppressToast: true });
      setData(response.data);
      setResult(response.data.submission_result);
    } catch (err) {
      setError(err?.userMessage || "Your answer could not be saved. Try again.");
    } finally {
      setBusy(false);
    }
  }
  return <section className="panel space-y-5" aria-labelledby="interaction-title">
    <div className="flex flex-wrap items-start justify-between gap-3"><div>
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Interactive practice · version {interaction.version}{interaction.required ? " · Required" : " · Optional"}</p>
      <h2 className="mt-1 text-xl font-bold" id="interaction-title">{interaction.title}</h2>
    </div><V2Status status={progress.status} /></div>
    <p id="interaction-instructions">{interaction.instructions}</p>
    <form className="space-y-5" onSubmit={submit} aria-describedby="interaction-instructions">
      <Renderer content={interaction.content} value={answer} onChange={setAnswer} />
      <button className="btn-primary min-h-11 focus-visible:ring-2 focus-visible:ring-teal-600" type="submit" disabled={busy}>{busy ? "Checking..." : progress.attempts.length ? "Check again" : "Check answer"}</button>
    </form>
    {error ? <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p> : null}
    {result ? <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700" role="status" aria-live="polite">
      <p className="font-semibold">{result.passed ? "Passed" : "Try again"} · {result.score}%</p>
      <p className="mt-1">{result.feedback}</p>
      {result.correct_answer != null ? <div className="mt-2 text-sm"><p className="font-medium">Correct answer:</p>{Array.isArray(result.correct_answer) ? <ol className="ml-5 list-decimal">{result.correct_answer.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol> : <p>{result.correct_answer}</p>}</div> : null}
      {result.next_action ? <p className="mt-2 text-sm font-medium">Next: {result.next_action}</p> : null}
    </div> : null}
    <p className="text-sm text-slate-500">{progress.attempts.length} attempt{progress.attempts.length === 1 ? "" : "s"} saved. You can retry without penalty.</p>
  </section>;
}
