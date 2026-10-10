import { useCallback, useEffect, useState } from "react";
import { getV2Interaction, submitV2Interaction } from "../../services/api";
import { V2Error, V2Loading } from "./V2PageState";
import V2Status from "./V2Status";
import { interactionRenderers } from "./V2InteractionRenderers";
import V2NextStep from "./V2NextStep";

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

export default function V2Interaction({ moduleKey, interactionKey, embedded = false, onChanged }) {
  const [data, setData] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    setError("");
    setStale(false);
    setResult(null);
    setData(null);
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
    setResult(null);
    try {
      const response = await submitV2Interaction(moduleKey, interactionKey, interaction.version_id, responseFor(interaction.type, answer), { suppressToast: true });
      setData(response.data);
      setResult(response.data.submission_result);
      await onChanged?.();
    } catch (err) {
      setError(err?.userMessage || "Your answer could not be saved. Try again.");
      if (err?.response?.status === 409) {
        setStale(true);
      }
    } finally {
      setBusy(false);
    }
  }
  const Heading = embedded ? "h3" : "h1";
  const titleId = embedded ? `interaction-title-${interactionKey}` : "interaction-title";
  const instructionsId = embedded ? `interaction-instructions-${interactionKey}` : "interaction-instructions";
  return <section className="learning-section space-y-5" aria-labelledby={titleId}>
    <div className="flex flex-wrap items-start justify-between gap-3"><div>
      <p className="type-label">Try it{interaction.required ? " · Required" : " · Optional"}</p>
      <Heading className="type-page-title" id={titleId}>{interaction.title}</Heading>
    </div><V2Status status={progress.status} /></div>
    <p id={instructionsId}>{interaction.instructions}</p>
    <form className="space-y-5" onSubmit={submit} aria-describedby={instructionsId}>
      <fieldset disabled={busy || stale || Boolean(result)} className="min-w-0"><legend className="sr-only">Your answer</legend><Renderer content={interaction.content} value={answer} onChange={setAnswer} /></fieldset>
      {!result && !stale ? <button className="btn-primary min-h-11" type="submit" disabled={busy}>{busy ? "Checking..." : "Check answer"}</button> : null}
    </form>
    {error ? <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p> : null}
    {stale ? <button className="btn-primary" type="button" onClick={load}>Reload interaction</button> : null}
    {result ? <div className={`learning-feedback ${result.passed ? "learning-feedback-correct" : "learning-feedback-retry"}`} role="status" aria-live="polite">
      <p className="font-semibold">{result.passed ? "Correct" : "Not quite"}</p>
      <p className="mt-1">{result.feedback}</p>
      {result.passed && result.correct_answer != null ? <div className="mt-2 text-sm"><p className="font-medium">Correct answer:</p>{Array.isArray(result.correct_answer) ? <ol className="ml-5 list-decimal">{result.correct_answer.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol> : <p>{result.correct_answer}</p>}</div> : null}
      {result.passed ? <div className="mt-4 flex flex-wrap items-center gap-3"><V2NextStep moduleKey={moduleKey} /><button className="btn-quiet" type="button" onClick={() => setResult(null)}>Practice again</button></div> : <button className="btn-primary mt-4" type="button" onClick={() => setResult(null)}>Try again</button>}
    </div> : null}
    {progress.attempt_count ? <p className="type-meta">{progress.attempt_count} attempt{progress.attempt_count === 1 ? "" : "s"} saved.</p> : null}
  </section>;
}
