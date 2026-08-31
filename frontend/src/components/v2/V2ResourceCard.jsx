import { Check, ExternalLink } from "lucide-react";
import { useState } from "react";
import { recordV2Resource } from "../../services/api";
import V2Status from "./V2Status";

export default function V2ResourceCard({ resource, moduleKey, onChanged }) {
  const [busy, setBusy] = useState(false);
  async function update(activity) {
    setBusy(true);
    try {
      await recordV2Resource(moduleKey, resource.key, activity, { suppressToast: true });
      await onChanged();
    } finally {
      setBusy(false);
    }
  }
  return <article className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${resource.required ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{resource.required ? "Required" : "Optional"}</span><h3 className="mt-3 font-bold">{resource.title}</h3><p className="mt-1 text-sm text-slate-500">{resource.provider || "Learning resource"} · {resource.type?.replaceAll("_", " ")}{resource.duration ? ` · ${resource.duration}` : ""}</p></div>{resource.completed ? <V2Status status="completed" /> : null}</div>
    <div className="mt-4 flex flex-wrap gap-2">
      {resource.url ? <a className="btn-secondary inline-flex items-center gap-2" href={resource.url} onClick={() => update({ opened: true })} target="_blank" rel="noopener noreferrer">Open resource <ExternalLink size={15} aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span></a> : <span className="text-sm text-slate-500">Resource link unavailable</span>}
      <button className="btn-secondary inline-flex items-center gap-2" disabled={busy || resource.completed} onClick={() => update({ completed: true })} type="button">{resource.completed ? "Completed" : "Mark completed"}{resource.completed ? <Check size={15} aria-hidden="true" /> : null}</button>
    </div>
    {resource.opened_at && !resource.completed ? <p className="mt-3 text-xs text-slate-500">Opened. Mark it complete when you finish.</p> : null}
  </article>;
}
