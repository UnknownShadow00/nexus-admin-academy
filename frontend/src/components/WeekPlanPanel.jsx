import { BookOpen, CheckCircle2, Circle, ClipboardList, FlaskConical, TerminalSquare, Ticket as TicketIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getWeekPlan } from "../services/api";
import { iconSizes } from "../utils/theme";

const SECTIONS = [
  { key: "lessons", label: "Lessons", Icon: BookOpen },
  { key: "quizzes", label: "Required Quizzes", Icon: ClipboardList },
  { key: "practice_quizzes", label: "Optional Practice", Icon: ClipboardList },
  { key: "remediation_quizzes", label: "Remediation", Icon: ClipboardList },
  { key: "cumulative_gate_quizzes", label: "Cumulative / Gate", Icon: ClipboardList },
  { key: "cli_labs", label: "Networking Labs", Icon: TerminalSquare },
  { key: "labs", label: "Labs", Icon: FlaskConical },
  { key: "tickets", label: "Tickets", Icon: TicketIcon },
];

const STATUS_STYLES = {
  done: "text-emerald-600 dark:text-emerald-400",
  in_review: "text-amber-600 dark:text-amber-400",
  in_progress: "text-amber-600 dark:text-amber-400",
  available: "text-slate-400 dark:text-slate-500",
};

function StatusIcon({ status }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.available;
  const Icon = status === "done" ? CheckCircle2 : Circle;
  return <Icon size={iconSizes.inline} className={`shrink-0 ${cls}`} aria-label={status} />;
}

export default function WeekPlanPanel() {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getWeekPlan(undefined, { suppressToast: true })
      .then((res) => { if (!cancelled) setPlan(res?.data || null); })
      .catch(() => { if (!cancelled) setError("Week plan unavailable right now."); });
    return () => { cancelled = true; };
  }, []);

  if (error) return null; // panel degrades silently; the rest of Home still works
  if (!plan) return <div className="panel h-32 animate-pulse dark:border-slate-700 dark:bg-slate-900" />;

  const sections = SECTIONS.map((s) => ({ ...s, items: plan[s.key] || [] })).filter((s) => s.items.length);
  const hasContent = sections.length > 0;

  return (
    <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">This Week</p>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Week {plan.week}{plan.role ? ` · ${plan.role}` : ""}
          </h2>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{plan.progress_percent}%</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">week complete</p>
        </div>
      </div>

      {plan.next_action ? (
        <Link
          to={plan.next_action.route || "/learning-path"}
          className="flex items-center justify-between gap-3 rounded-xl border border-blue-200 bg-blue-50/70 p-3 text-sm font-medium text-blue-800 hover:border-blue-300 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200"
        >
          <span>Next up: {plan.next_action.title}</span>
          <span aria-hidden="true">→</span>
        </Link>
      ) : hasContent ? (
        <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
          Everything for this week is done. Review flashcards or work ahead.
        </p>
      ) : null}

      {hasContent ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {sections.map(({ key, label, Icon, items }) => (
            <div key={key} className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                <Icon size={iconSizes.inline} aria-hidden="true" />
                {label}
                <span className="text-xs font-normal text-slate-400">
                  {items.filter((i) => i.status === "done").length}/{items.length}
                </span>
              </div>
              <ul className="space-y-1">
                {items.map((item) => (
                  <li key={`${key}-${item.id}`}>
                    <Link to={item.route || "#"} className="flex items-center gap-2 rounded-lg p-1.5 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                      <StatusIcon status={item.status} />
                      <span className="truncate">{item.title}</span>
                      {item.label ? <span className="ml-auto shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] dark:bg-slate-800">{item.label}</span> : null}
                      {item.status === "in_review" && <span className="ml-auto shrink-0 text-xs text-amber-600 dark:text-amber-400">in review</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          No content is scheduled for week {plan.week} yet.
        </p>
      )}
    </section>
  );
}
