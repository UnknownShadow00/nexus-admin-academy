import { Link } from "react-router-dom";

export default function V2CorrectionAlerts({ corrections = [] }) {
  if (!corrections.length) return null;
  return <section aria-label="Outstanding corrections" className="rounded-2xl border border-rose-300 bg-rose-50 p-5 text-rose-950 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-100">
    <h2 className="text-xl font-bold">Needs correction ({corrections.length})</h2>
    <p className="mt-1">Your mentor has feedback on practical work. You can keep learning and return to fix it.</p>
    <ul className="mt-4 space-y-3">{corrections.map((item) => <li className="rounded-xl bg-white p-4 dark:bg-slate-900" key={`${item.module_key}-${item.assessment_key}`}><p className="font-semibold">{item.stage_title} · {item.practical_title}</p><p className="mt-1 whitespace-pre-wrap text-sm">Mentor feedback: {item.feedback || "Review your submission and improve the evidence."}</p><Link className="btn-primary mt-3 inline-flex" to={item.route}>Fix & resubmit →</Link></li>)}</ul>
  </section>;
}
