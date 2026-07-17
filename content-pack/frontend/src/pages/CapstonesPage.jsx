import { useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import Spinner from "../components/Spinner";
import PageHeader from "../components/ui/PageHeader";
import { getCapstones } from "../services/api";

const statusConfig = {
  not_started: { label: "Not Started", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  in_progress: { label: "In Progress", cls: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" },
  submitted: { label: "Submitted", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" },
};

export default function CapstonesPage() {
  const [week, setWeek] = useState("");
  const [loading, setLoading] = useState(true);
  const [capstones, setCapstones] = useState([]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      try {
        const res = await getCapstones(week ? Number(week) : undefined, { suppressToast: true });
        if (!cancelled) {
          setCapstones(Array.isArray(res.data) ? res.data : []);
        }
      } catch {
        if (!cancelled) {
          setCapstones([]);
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
  }, [week]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <PageHeader
          title="Capstone Projects"
          subtitle="Scenario-based module projects where you document your approach, findings, and final deliverables."
        />
        <div className="mt-4 flex flex-wrap gap-2">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
            Week:
            <input
              className="input-field max-w-24"
              type="number"
              min={1}
              placeholder="All"
              value={week}
              onChange={(event) => setWeek(event.target.value)}
            />
          </label>
        </div>
      </div>

      {loading ? (
        <div className="panel dark:border-slate-700 dark:bg-slate-900">
          <Spinner text="Loading capstones..." />
        </div>
      ) : capstones.length === 0 ? (
        <EmptyState
          icon={<ClipboardCheck size={40} className="text-slate-300" />}
          title="No capstones published"
          message="Try another week number or check back after new capstone projects are published."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {capstones.map((capstone) => (
            <article key={capstone.id} className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
              <div className="space-y-2">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{capstone.title}</h2>
                <p className="text-sm text-slate-600 dark:text-slate-300">{capstone.description}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  Week {capstone.week_number}
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {capstone.estimated_hours} hrs
                </span>
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${(statusConfig[capstone.status] || statusConfig.not_started).cls}`}>
                  {(statusConfig[capstone.status] || statusConfig.not_started).label}
                </span>
              </div>

              <Link to={`/capstones/${capstone.id}`} className="btn-primary inline-flex w-full justify-center">
                {capstone.status === "submitted" ? "View Submission" : "Open Capstone"}
              </Link>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
