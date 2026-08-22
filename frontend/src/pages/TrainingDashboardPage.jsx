import { ArrowRight, Check, ChevronRight, Clock, Lock } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import TrainingSubnav from "../components/TrainingSubnav";
import { getTrainingDashboard } from "../services/api";

const statusLabels = { available: "Available", not_started: "Available", in_progress: "Current", complete: "Complete", locked: "Locked" };

function LoadingState() {
  return <main className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6"><div className="h-12 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" /><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;
}

function StatusBadge({ status }) {
  const classes = status === "locked"
    ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
    : status === "complete"
      ? "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300"
      : "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300";
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${classes}`}>{status === "locked" ? <Lock size={12} /> : status === "complete" ? <Check size={12} /> : null}{statusLabels[status] || status}</span>;
}

function ModuleCard({ currentModuleId, module }) {
  const card = (
    <div className={`h-full rounded-xl border p-4 transition ${module.stable_id === currentModuleId ? "border-blue-500 bg-blue-50 shadow-sm dark:border-blue-500 dark:bg-blue-950/20" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"}`}>
      <div className="flex items-start justify-between gap-3">
        <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Module</p><h3 className="mt-1 font-bold text-slate-900 dark:text-white">{module.title}</h3></div>
        <StatusBadge status={module.status} />
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">{module.purpose}</p>
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400"><span>{module.required_complete} of {module.required_total} required</span>{module.required_estimated_minutes ? <span className="inline-flex items-center gap-1"><Clock size={13} />About {Math.ceil(module.required_estimated_minutes / 60)} hr</span> : null}</div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><div className="h-full rounded-full bg-blue-600" style={{ width: `${module.completion_percent}%` }} /></div>
      {module.lock_reason ? <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{module.lock_reason}</p> : null}
    </div>
  );
  return module.locked ? <div>{card}</div> : <Link to={module.route} className="rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">{card}</Link>;
}

export default function TrainingDashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    getTrainingDashboard({ suppressToast: true })
      .then((response) => active && setData(response.data))
      .catch(() => active && setError("Your learning path could not be loaded. Please try again."));
    return () => { active = false; };
  }, []);

  const allModules = useMemo(() => (data?.stages || []).flatMap((stage) => stage.modules), [data]);
  if (!data && !error) return <LoadingState />;
  if (error) return <main className="mx-auto max-w-3xl p-6"><div role="alert" className="panel border-red-200 text-red-700 dark:border-red-900 dark:text-red-300">{error}</div></main>;

  const stage = data.current_stage;
  const module = data.current_module;
  const next = data.current_activity;
  const actionRoute = next?.destination_route || module?.route || "/training/content";
  const actionLabel = data.training_complete ? "Review Learning Path" : module?.required_complete ? "Continue Module" : "Start Module";
  const currentIndex = allModules.findIndex((item) => item.stable_id === module?.stable_id);
  const upNext = currentIndex >= 0 ? allModules[currentIndex + 1] : null;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
      <div><h1 className="text-3xl font-bold text-slate-950 dark:text-white">Learning Path</h1><p className="mt-1 text-slate-600 dark:text-slate-300">Your stages, modules, and next activity—without the calendar clutter.</p></div>
      <TrainingSubnav />
      {module ? (
        <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 p-5 text-white shadow-lg sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-100">{data.training_complete ? "Training Complete" : "Current Stage"}</p>
          <h2 className="mt-2 text-xl font-bold text-blue-100">{stage?.title}</h2>
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.18em] text-blue-200">Current Module</p>
          <h3 className="mt-1 text-2xl font-bold sm:text-3xl">{module.title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-blue-100">{module.purpose}</p>
          <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0 flex-1"><div className="mb-2 flex justify-between text-sm"><span>{module.required_complete} of {module.required_total} required activities complete</span><strong>{module.completion_percent}%</strong></div><div className="h-3 overflow-hidden rounded-full bg-blue-950/40"><div className="h-full rounded-full bg-white transition-all" style={{ width: `${module.completion_percent}%` }} /></div>{next ? <p className="mt-3 truncate text-sm text-blue-100">Current activity: {next.activity_label} — {next.title}</p> : null}</div>
            <Link to={actionRoute} className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-blue-700 shadow hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">{actionLabel}<ArrowRight size={18} /></Link>
          </div>
        </section>
      ) : <section className="panel"><h2 className="text-xl font-semibold">No active training modules</h2><p className="mt-2 text-slate-600 dark:text-slate-300">Ask an administrator to check the curriculum structure.</p></section>}

      {upNext ? <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"><p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Up Next</p><h2 className="mt-1 font-bold text-slate-900 dark:text-white">{upNext.title}</h2><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{upNext.purpose}</p><p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{upNext.locked ? (upNext.lock_reason || "Finish your current module to unlock this.") : "Available after your current module."}</p></section> : null}

      <section className="space-y-4" aria-label="Full learning path">
        {(data.stages || []).map((pathStage) => (
          <details className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900" key={pathStage.stable_id} defaultOpen={pathStage.stable_id === stage?.stable_id}>
            <summary className="cursor-pointer list-none px-4 py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"><span className="flex items-center justify-between gap-3"><span className="inline-flex min-w-0 items-center gap-2"><ChevronRight className="shrink-0 transition-transform [details[open]_&]:rotate-90" size={17} /><span><span className="block text-xs font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400">Stage {pathStage.display_order}</span><span className="block truncate font-bold text-slate-900 dark:text-white">{pathStage.title}</span></span></span><StatusBadge status={pathStage.status} /></span></summary>
            <div className="border-t border-slate-200 p-4 dark:border-slate-700"><p className="mb-4 text-sm text-slate-600 dark:text-slate-300">{pathStage.description}</p><div className="grid gap-3 md:grid-cols-2">{pathStage.modules.map((pathModule) => <ModuleCard currentModuleId={module?.stable_id} key={pathModule.stable_id} module={pathModule} />)}</div></div>
          </details>
        ))}
      </section>
    </main>
  );
}
