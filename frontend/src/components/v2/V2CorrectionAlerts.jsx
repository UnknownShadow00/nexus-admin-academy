import { Link } from "react-router-dom";

export default function V2CorrectionAlerts({ corrections = [] }) {
  if (!corrections.length) return null;
  return <section aria-label="Changes requested for practical work" className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-amber-950 dark:border-amber-700 dark:bg-amber-950/20 dark:text-amber-100">
    <h2 className="text-xl font-bold">Changes requested ({corrections.length})</h2>
    <p className="mt-1">Your mentor left feedback on practical work. You can keep learning while you update it.</p>
    <ul className="mt-4 space-y-3">{corrections.map((item) => <li className="rounded-xl bg-white p-4 dark:bg-slate-900" key={`${item.module_key}-${item.assessment_key}`}><p className="font-semibold">{item.stage_title} · {item.practical_title}</p><p className="mt-1 whitespace-pre-wrap text-sm">Mentor feedback: {item.feedback || "Review your submission and improve the evidence."}</p><Link className="btn-primary mt-3 inline-flex" to={item.route}>Fix & resubmit →</Link></li>)}</ul>
  </section>;
}
