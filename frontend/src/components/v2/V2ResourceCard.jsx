import { Check, ExternalLink } from "lucide-react";
import { useState } from "react";
import { recordV2Resource } from "../../services/api";
import V2Status from "./V2Status";

export default function V2ResourceCard({ resource, moduleKey, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function update(activity) {
    setBusy(true);
    setError("");
    try {
      await recordV2Resource(moduleKey, resource.key, activity, { suppressToast: true });
      await onChanged();
    } catch (err) {
      setError(err?.userMessage || "We couldn't save this resource update. Try again.");
    } finally {
      setBusy(false);
    }
  }
  return <article className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${resource.required ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{resource.required ? "Required" : "Optional"}</span><h3 className="mt-3 font-bold">{resource.title}</h3><p className="mt-1 text-sm text-slate-500">{resource.provider || "Learning resource"} · {resource.type?.replaceAll("_", " ")}{resource.duration ? ` · ${resource.duration}` : ""}</p></div>{resource.completed ? <V2Status status="completed" /> : null}</div>
    <div className="mt-4 flex flex-wrap gap-2">
      {resource.url && !resource.completed ? <a className="btn-secondary inline-flex items-center gap-2" href={resource.url} onClick={() => update({ opened: true })} target="_blank" rel="noopener noreferrer">{resource.opened_at ? "Open again" : resource.required ? "Open required resource" : "Open optional resource"}<ExternalLink size={15} aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span></a> : !resource.url ? <span className="text-sm text-slate-500">This resource link is not available. Return to the module and choose another activity.</span> : null}
      {resource.completed ? <span className="inline-flex items-center gap-2 rounded-lg bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"><Check size={15} aria-hidden="true" />Completed</span> : resource.opened_at ? <button className="btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => update({ completed: true })} type="button">{busy ? "Saving..." : "I finished this"}</button> : null}
    </div>
    {resource.opened_at && !resource.completed ? <p className="mt-3 text-sm font-semibold text-blue-700 dark:text-blue-300" role="status">In progress — finish the resource, then choose “I finished this.”</p> : null}
    {error ? <p className="mt-3 text-sm text-rose-700 dark:text-rose-300" role="alert">{error}</p> : null}
  </article>;
}
