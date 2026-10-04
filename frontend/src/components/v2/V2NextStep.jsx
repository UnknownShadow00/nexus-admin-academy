import { useEffect, useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";
import { getV2Module } from "../../services/api";

export default function V2NextStep({ moduleKey, label = "Next step", showDescription = false, pendingReview = false }) {
  const [next, setNext] = useState(null);
  const [resolved, setResolved] = useState(false);
  const inRouter = useInRouterContext();
  useEffect(() => {
    let active = true;
    if (typeof getV2Module !== "function") { setResolved(true); return undefined; }
    getV2Module(moduleKey, { suppressToast: true }).then(({ data }) => {
      if (active) { setNext(data.continue); setResolved(true); }
    }).catch(() => { if (active) { setNext(null); setResolved(true); } });
    return () => { active = false; };
  }, [moduleKey]);
  const canContinue = Boolean(next?.route && next.kind === "next_stage" && next.route !== window.location.pathname);
  const samePage = next?.route === window.location.pathname;
  const courseFallback = !next?.route || samePage || next.kind === "review_pending" || (pendingReview && !canContinue);
  const route = courseFallback ? "/learning-v2" : next.route;
  const actionLabel = courseFallback ? "Back to My Course" : next?.label || label;
  if (!resolved) return <span className="text-sm text-slate-500" role="status">Finding your next step…</span>;
  const action = inRouter ? <Link className="btn-primary inline-flex items-center gap-2" to={route}>{actionLabel} →</Link> : <a className="btn-primary inline-flex items-center gap-2" href={route}>{actionLabel} →</a>;
  if (pendingReview) return <><p className="mt-2">Your practical was sent to your mentor. {canContinue ? "You can keep learning while your mentor reviews it." : "You can review your course while your mentor reviews it."}</p><div className="mt-4">{action}</div></>;
  return showDescription ? <div><p className="mb-3 text-sm font-medium">Next: {actionLabel}</p>{action}</div> : action;
}
