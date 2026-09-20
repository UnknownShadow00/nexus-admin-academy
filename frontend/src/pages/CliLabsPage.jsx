import { CheckCircle2, ChevronDown, ChevronRight, Clock, Network } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import BackLink from "../components/BackLink";
import PageHeader from "../components/ui/PageHeader";
import { cliLabCompartments } from "../features/cli-labs/data/lessonCatalog";
import { getCliLabs } from "../services/api";

export default function CliLabsPage() {
  const [completionById, setCompletionById] = useState({});
  const [availableIds, setAvailableIds] = useState(null);
  const [catalogError, setCatalogError] = useState(null);
  const [requestVersion, setRequestVersion] = useState(0);
  const [expandedCompartmentIds, setExpandedCompartmentIds] = useState(() => new Set());

  useEffect(() => {
    let cancelled = false;
    setCatalogError(null);
    setAvailableIds(null);
    getCliLabs({ suppressToast: true })
      .then((response) => {
        if (cancelled) return;
        const rows = Array.isArray(response.data) ? response.data : [];
        setCompletionById(Object.fromEntries(rows.map((row) => [row.id, row])));
        setAvailableIds(new Set(rows.map((row) => row.id)));
      })
      .catch((error) => {
        if (!cancelled) {
          setCompletionById({});
          setCatalogError(error?.userMessage || "Unable to load networking labs. Please try again.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [requestVersion]);

  const visibleCompartments = useMemo(() => (cliLabCompartments || []).map((compartment) => ({
    ...compartment,
    lessons: (compartment.lessons || []).filter((lesson) => availableIds?.has(lesson.id)),
  })).filter((compartment) => compartment.lessons.length), [availableIds]);
  const visibleLessons = visibleCompartments.flatMap((compartment) => compartment.lessons);
  const completedCount = useMemo(() => visibleLessons.filter((lesson) => completionById[lesson.id]?.completed).length, [completionById, visibleLessons]);

  function toggleCompartment(compartmentId) {
    setExpandedCompartmentIds((current) => {
      const next = new Set(current);
      if (next.has(compartmentId)) next.delete(compartmentId);
      else next.add(compartmentId);
      return next;
    });
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <BackLink fallbackLabel="Labs" fallbackTo="/labs" />
      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <PageHeader
          title="Networking Labs"
          subtitle="Cisco IOS command practice for Network+ and CCNA-adjacent skills."
          actions={
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
              {completedCount}/{visibleLessons.length} complete
            </span>
          }
        />
      </div>

      {catalogError ? (
        <section className="panel text-center" role="alert">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Networking labs unavailable</h2>
          <p className="mt-2 text-slate-600 dark:text-slate-300">{catalogError}</p>
          <button className="btn-primary mt-4" type="button" onClick={() => setRequestVersion((value) => value + 1)}>
            Try again
          </button>
        </section>
      ) : null}

      {!catalogError && availableIds?.size === 0 ? <section className="panel text-center"><h2 className="text-xl font-bold text-slate-900 dark:text-white">Networking labs unlock later</h2><p className="mt-2 text-slate-600 dark:text-slate-300">Complete orientation to reach the first CLI lessons. Switch and network labs unlock after A+ and the first half of your active Network+ modules.</p><Link className="btn-primary mt-4 inline-flex" to="/">Return to Today</Link></section> : null}

      {visibleCompartments.map((compartment) => {
        const lessons = compartment.lessons || [];
        const expanded = expandedCompartmentIds.has(compartment.compartmentId);
        const topicCompleted = lessons.filter((lesson) => completionById[lesson.id]?.completed).length;

        return (
          <section key={compartment.compartmentId} className="space-y-4">
            <button
              type="button"
              onClick={() => toggleCompartment(compartment.compartmentId)}
              className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left shadow-sm transition hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-500 dark:hover:bg-slate-800/70"
              aria-expanded={expanded}
            >
              <span className="flex min-w-0 items-center gap-3">
                {expanded ? (
                  <ChevronDown size={19} className="shrink-0 text-slate-500 dark:text-slate-300" />
                ) : (
                  <ChevronRight size={19} className="shrink-0 text-slate-500 dark:text-slate-300" />
                )}
                <Network size={18} className="shrink-0 text-blue-600 dark:text-blue-300" />
                <span className="truncate text-lg font-semibold text-slate-900 dark:text-slate-100">{compartment.compartmentTitle}</span>
              </span>
              <span className="shrink-0 rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                {topicCompleted}/{lessons.length} complete
              </span>
            </button>

            {expanded ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {lessons.map((lesson, index) => {
                  const completed = completionById[lesson.id]?.completed;
                  return (
                    <Link
                      key={lesson.id}
                      to={`/cli-labs/${lesson.id}`}
                      className="group rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-500"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                            Lab {index + 1}
                          </div>
                          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{lesson.title}</h3>
                        </div>
                        {completed ? <CheckCircle2 className="shrink-0 text-emerald-500" size={20} /> : null}
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2 text-xs font-medium">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {lesson.difficulty}
                        </span>
                        <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          <Clock size={13} />
                          {lesson.estimatedMinutes} min
                        </span>
                        {lesson.type ? (
                          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                            {lesson.type}
                          </span>
                        ) : null}
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : null}
          </section>
        );
      })}
    </main>
  );
}
