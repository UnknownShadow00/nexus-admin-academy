import { CheckCircle2, Circle } from "lucide-react";
import { objectiveStatuses } from "../engine/objectiveTracker";

export default function ObjectivesPanel({ lesson, progress, complete }) {
  const objectives = objectiveStatuses(lesson, progress);

  return (
    <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Objectives</h2>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${complete ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>
          {objectives.filter((item) => item.complete).length}/{objectives.length}
        </span>
      </div>
      <ul className="space-y-3">
        {objectives.map((objective) => (
          <li key={objective.id} className="flex items-start gap-3 text-sm">
            {objective.complete ? (
              <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-500" size={18} />
            ) : (
              <Circle className="mt-0.5 shrink-0 text-slate-400" size={18} />
            )}
            <span className={objective.complete ? "text-slate-500 line-through dark:text-slate-400" : "text-slate-700 dark:text-slate-200"}>
              {objective.label}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
