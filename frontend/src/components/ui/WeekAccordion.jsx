import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export default function WeekAccordion({ items, renderItem, gridClassName }) {
  const [openWeeks, setOpenWeeks] = useState(() => new Set());

  const weekGroups = useMemo(() => {
    const groups = new Map();

    items.forEach((item) => {
      const weekNumber = item.week_number;
      const weekItems = groups.get(weekNumber) || [];
      weekItems.push(item);
      groups.set(weekNumber, weekItems);
    });

    return Array.from(groups.entries()).sort(([weekA], [weekB]) => weekA - weekB);
  }, [items]);

  const allOpen = weekGroups.every(([weekNumber]) => openWeeks.has(weekNumber));

  const toggleWeek = (weekNumber) => {
    setOpenWeeks((current) => {
      const next = new Set(current);
      if (next.has(weekNumber)) {
        next.delete(weekNumber);
      } else {
        next.add(weekNumber);
      }
      return next;
    });
  };

  const toggleAll = () => {
    setOpenWeeks(allOpen ? new Set() : new Set(weekGroups.map(([weekNumber]) => weekNumber)));
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          type="button"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          onClick={toggleAll}
        >
          {allOpen ? "Collapse All" : "Expand All"}
        </button>
      </div>

      {weekGroups.map(([weekNumber, weekItems]) => {
        const isOpen = openWeeks.has(weekNumber);

        return (
          <section key={weekNumber} className="panel overflow-hidden p-0 dark:border-slate-700 dark:bg-slate-900">
            <button
              type="button"
              className="flex w-full items-center gap-2 px-4 py-3 text-left text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              aria-expanded={isOpen}
              onClick={() => toggleWeek(weekNumber)}
            >
              {isOpen ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
              <span className="font-semibold">Week {weekNumber}</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                ({weekItems.length})
              </span>
            </button>

            {isOpen ? (
              <div className="border-t border-slate-200 p-4 dark:border-slate-700">
                <div className={gridClassName}>{weekItems.map(renderItem)}</div>
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
