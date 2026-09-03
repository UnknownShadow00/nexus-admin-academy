import { AlertCircle } from "lucide-react";
import { Link } from "react-router-dom";
import Spinner from "../Spinner";

export function V2Loading({ text = "Loading your learning..." }) {
  return <main className="mx-auto max-w-5xl p-6"><div className="panel" role="status"><Spinner text={text} /></div></main>;
}

export function V2Error({ title = "We couldn't load this page", message, onRetry, moduleRoute }) {
  return <main className="mx-auto max-w-2xl p-6"><div className="panel text-center" role="alert"><AlertCircle className="mx-auto text-rose-500" size={32} aria-hidden="true" /><h1 className="mt-3 text-xl font-bold">{title}</h1><p className="mt-2 text-slate-600 dark:text-slate-300">{message || "Try again in a moment. If it keeps happening, ask your mentor for help."}</p><div className="mt-5 flex flex-wrap justify-center gap-3">{onRetry ? <button className="btn-primary" onClick={onRetry} type="button">Try again</button> : null}{moduleRoute ? <Link className="btn-secondary" to={moduleRoute}>Back to module</Link> : null}<Link className="btn-secondary" to="/">Back to Today</Link></div></div></main>;
}
