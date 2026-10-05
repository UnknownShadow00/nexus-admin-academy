import { ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { recordV2Resource } from "../../services/api";
import Banner from "../ui/Banner";
import TeachingCardViewer from "./TeachingCardViewer";
import V2Status from "./V2Status";

export default function V2ResourceCard({ resource, moduleKey, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [confirmedStatus, setConfirmedStatus] = useState(null);
  const opener = useRef(null);
  const internalCard = resource.url?.startsWith("/v2-interactions/beginner-s4-") && resource.url.endsWith(".svg");
  useEffect(() => setConfirmedStatus(null), [resource.key, resource.status, resource.opened_at, resource.watched_at]);
  async function update(activity) {
    setBusy(true);
    setError("");
    try {
      const response = await recordV2Resource(moduleKey, resource.key, activity, { suppressToast: true });
      if (response.data?.status) setConfirmedStatus(response.data.status);
      await onChanged?.();
    } catch (err) {
      setError(err?.userMessage || "We couldn't save this resource update. Try again.");
    } finally {
      setBusy(false);
    }
  }
  function openCard() { setOpen(true); void update({ opened: true }); }
  return <article className="learning-resource">
    <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><p className="type-label">{resource.type?.replaceAll("_", " ") || "Resource"}{resource.required ? " · Required" : " · Optional"}</p><h3 className="mt-1 break-words font-semibold">{resource.title}</h3>{resource.provider ? <p className="type-meta mt-1">{resource.provider}{resource.duration ? ` · ${resource.duration}` : ""}</p> : null}</div><V2Status status={confirmedStatus || resource.status} /></div>
    <div className="mt-4 flex flex-wrap gap-2">
      {resource.url ? internalCard ? <button ref={opener} className="btn-secondary" onClick={openCard} type="button">{resource.opened_at || confirmedStatus === "viewed" ? "View again" : "View teaching card"}</button> : <a className="btn-secondary inline-flex items-center gap-2" href={resource.url} onClick={() => update({ opened: true })} target="_blank" rel="noopener noreferrer">{resource.opened_at || confirmedStatus === "viewed" ? "Open again" : resource.type === "video" ? "Open video" : "Open resource"}<ExternalLink size={15} aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span></a> : <span className="type-meta">This resource link is not available. Return to the stage and choose another activity.</span>}
      {resource.type === "video" && resource.opened_at && !resource.watched_at ? <button className="btn-primary inline-flex items-center gap-2" disabled={busy} onClick={() => update({ watched: true })} type="button">{busy ? "Saving..." : "I watched this"}</button> : null}
    </div>
    {resource.type === "video" && resource.watched_at ? <p className="mt-3 text-sm font-semibold text-amber-700 dark:text-amber-300" role="status">Watched (self reported). Viewing alone does not grant mastery.</p> : null}
    {error ? <div className="mt-3"><Banner variant="error">{error}</Banner></div> : null}
    {open ? <TeachingCardViewer title={resource.title} src={resource.url} opener={opener} onClose={() => setOpen(false)} /> : null}
  </article>;
}
