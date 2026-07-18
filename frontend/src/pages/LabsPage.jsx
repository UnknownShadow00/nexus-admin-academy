import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import Spinner from "../components/Spinner";
import { DifficultyBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import WeekAccordion from "../components/ui/WeekAccordion";
import { getLabs } from "../services/api";

const statusConfig = {
  not_started: { label: "Not Started", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  in_progress: { label: "In Progress", cls: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" },
  submitted: { label: "Submitted", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" },
};

export default function LabsPage() {
  const [week, setWeek] = useState(1);
  const [allWeeks, setAllWeeks] = useState(false);
  const [loading, setLoading] = useState(true);
  const [labs, setLabs] = useState([]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      try {
        const res = await getLabs(allWeeks ? undefined : week, { suppressToast: true });
        if (!cancelled) {
          setLabs(Array.isArray(res.data) ? res.data : []);
        }
      } catch {
        if (!cancelled) {
          setLabs([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [week, allWeeks]);

  const renderLab = (lab) => (
    <article key={lab.id} className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{lab.title}</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">{lab.description}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <DifficultyBadge level={lab.difficulty} />
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Week {lab.week_number}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {lab.lab_type}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {lab.estimated_minutes} min
        </span>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${(statusConfig[lab.status] || statusConfig.not_started).cls}`}>
          {(statusConfig[lab.status] || statusConfig.not_started).label}
        </span>
      </div>

      <Link to={`/labs/${lab.id}`} className="btn-primary inline-flex w-full justify-center">
        {lab.status === "submitted" ? "View Submission" : "Open Lab"}
      </Link>
    </article>
  );

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <PageHeader title="Lab Exercises" subtitle="Hands-on text-based exercises you can complete without a VM." />
        <div className="mt-4 flex flex-wrap gap-2">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
            Week:
            <input
              className="input-field max-w-24 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500"
              type="number"
              min={1}
              value={week}
              disabled={allWeeks}
              onChange={(event) => setWeek(Number(event.target.value || 1))}
            />
          </label>
          <button
            type="button"
            className={`rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium dark:border-slate-700 ${
              allWeeks
                ? "bg-blue-600 text-white"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            }`}
            onClick={() => setAllWeeks((current) => !current)}
          >
            All Weeks
          </button>
        </div>
      </div>

      {loading ? (
        <div className="panel dark:border-slate-700 dark:bg-slate-900">
          <Spinner text="Loading labs..." />
        </div>
      ) : labs.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={40} className="text-slate-300" />}
          title="No labs published"
          message="Try another week number or check back after new exercises are published."
        />
      ) : allWeeks ? (
        <WeekAccordion items={labs} renderItem={renderLab} gridClassName="grid gap-4 md:grid-cols-2" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {labs.map(renderLab)}
        </div>
      )}
    </main>
  );
}
