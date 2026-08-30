import { ArrowRight, BookOpen, CheckCircle2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getV2Learning } from "../../services/api";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";

export default function V2LearningPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    getV2Learning({ suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.userMessage || "Your learning path is unavailable right now."));
  }, []);
  useEffect(load, [load]);
  if (error) return <V2Error message={error} onRetry={load} />;
  if (!data) return <V2Loading />;
  if (!data.current) return <V2Error title="No module is available yet" message="Your mentor can let you know when learning content is ready." />;
  const current = data.current;
  const lessons = current.progress.lessons;
  const examCode = current.certification.version.exam_codes?.[0] || current.certification.version.label;
  return <main className="mx-auto max-w-5xl space-y-6 p-4 pb-20 sm:p-6">
    <header>
      <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">Your learning</p>
      <h1 className="mt-1 text-3xl font-bold text-slate-950 dark:text-white">{current.certification.name}</h1>
      <p className="mt-1 text-slate-600 dark:text-slate-300">{current.certification.version.label} · {examCode}</p>
    </header>
    <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-blue-700 to-slate-950 p-5 text-white shadow-lg sm:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-200">Current module</p>
          <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{current.module.title}</h2>
          <p className="mt-3 text-blue-100">{current.module.description}</p>
          <div className="mt-5 flex flex-wrap gap-3 text-sm">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5"><BookOpen size={16} aria-hidden="true" />{lessons.completed} of {lessons.total} lessons completed</span>
            {current.progress.module_complete ? <span className="inline-flex items-center gap-2 rounded-full bg-emerald-400/20 px-3 py-1.5"><CheckCircle2 size={16} aria-hidden="true" />Module complete</span> : null}
          </div>
        </div>
        <Link className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-blue-800 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" to={current.continue.route}>
          {current.continue.label}<ArrowRight size={18} aria-hidden="true" />
        </Link>
      </div>
    </section>
    <section className="panel">
      <h2 className="text-lg font-bold">What comes next</h2>
      <p className="mt-2 text-slate-600 dark:text-slate-300">{current.continue.title}</p>
      <Link className="mt-3 inline-flex font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to={`/learning-v2/modules/${current.module.key}`}>View the whole module →</Link>
    </section>
    <section aria-labelledby="modules-heading">
      <h2 id="modules-heading" className="text-xl font-bold">A+ modules</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {data.modules.map((item) => {
          const complete = item.progress.module_complete;
          const started = item.progress.lessons.completed > 0 || Object.values(item.progress.assessments || {}).some((value) => value?.status && value.status !== "not_started");
          return <Link className="panel block hover:border-blue-300" key={item.module.key} to={`/learning-v2/modules/${item.module.key}`}>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.certification.version.label}</p>
            <h3 className="mt-1 font-bold">{item.module.title}</h3>
            <p className="mt-2 text-sm text-slate-500">{complete ? "Complete" : started ? "In progress" : "Not started"} · {item.progress.lessons.completed}/{item.progress.lessons.total} lessons</p>
          </Link>;
        })}
      </div>
    </section>
  </main>;
}
