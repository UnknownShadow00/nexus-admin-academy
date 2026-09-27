import { ExternalLink } from "lucide-react";
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
    <div className="flex flex-wrap items-start justify-between gap-3"><div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${resource.required ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{resource.required ? "Required" : "Optional"}</span><h3 className="mt-3 font-bold">{resource.title}</h3><p className="mt-1 text-sm text-slate-500">{resource.provider || "Learning resource"} · {resource.type?.replaceAll("_", " ")}{resource.duration ? ` · ${resource.duration}` : ""}</p></div><V2Status status={resource.status} /></div>
    <div className="mt-4 flex flex-wrap gap-2">
      {resource.url ? <a className="btn-secondary inline-flex items-center gap-2" href={resource.url} onClick={() => update({ opened: true })} target="_blank" rel="noopener noreferrer">{resource.opened_at ? "Open again" : resource.type === "video" ? "Open video" : "Open resource"}<ExternalLink size={15} aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span></a> : <span className="text-sm text-slate-500">This resource link is not available. Return to the module and choose another activity.</span>}
      {resource.type === "video" && resource.opened_at && !resource.watched_at ? <button className="btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => update({ watched: true })} type="button">{busy ? "Saving..." : "I watched this"}</button> : null}
    </div>
    {resource.type === "video" && resource.watched_at ? <p className="mt-3 text-sm font-semibold text-amber-700 dark:text-amber-300" role="status">Watched (self reported). Viewing alone does not grant mastery.</p> : null}
    {error ? <p className="mt-3 text-sm text-rose-700 dark:text-rose-300" role="alert">{error}</p> : null}
  </article>;
}
