import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import EmptyState from "../components/EmptyState";
import PrerequisiteLock, { getPrerequisiteLock } from "../components/PrerequisiteLock";
import PageHeader from "../components/ui/PageHeader";
import LabRunner from "../features/cli-labs/components/LabRunner";
import { findCliLesson, nextCliLesson } from "../features/cli-labs/data/lessonCatalog";
import { getCliLab } from "../services/api";
import { setMonitoringContext } from "../monitoring/sentry";

export default function CliLabPage() {
  const { labId } = useParams();
  const lesson = findCliLesson(labId);
  const nextLesson = nextCliLesson(labId);
  const [completed, setCompleted] = useState(false);
  const [prerequisiteLock, setPrerequisiteLock] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    if (!labId) return;
    let cancelled = false;
    setLoaded(false);
    setLoadError(null);
    setPrerequisiteLock(null);
    getCliLab(labId, { suppressToast: true })
      .then((response) => {
        if (!cancelled) setCompleted(Boolean(response.data?.completed));
      })
      .catch((error) => {
        if (cancelled) return;
        setCompleted(false);
        const lock = getPrerequisiteLock(error);
        if (lock) setPrerequisiteLock(lock);
        else setLoadError(error?.userMessage || "Unable to load this networking lab. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [labId, requestVersion]);

  useEffect(() => {
    if (!lesson) return;
    setMonitoringContext({
      nexus_area: "lab",
      lab_template_id: lesson.id,
      module_name: lesson.title,
      activity_stable_id: lesson.id,
      activity_type: "networking_lab",
    });
  }, [lesson]);

  if (!lesson) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <EmptyState title="CLI lab not found" message="Return to the Networking Labs list and choose another exercise." />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <BackLink className="btn-secondary gap-2" fallbackLabel="Networking Labs" fallbackTo="/cli-labs" />
        {nextLesson ? (
          <Link to={`/cli-labs/${nextLesson.id}`} className="btn-secondary">
            Next: {nextLesson.title}
          </Link>
        ) : null}
      </div>
      <PageHeader
        title={lesson.title}
        subtitle={`${lesson.compartmentTitle} | ${lesson.difficulty} | ${lesson.estimatedMinutes} minutes`}
        actions={
          completed ? (
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
              Completed
            </span>
          ) : null
        }
      />
      <PrerequisiteLock lock={prerequisiteLock} />
      {loadError ? (
        <section className="panel text-center" role="alert">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Lab unavailable</h2>
          <p className="mt-2 text-slate-600 dark:text-slate-300">{loadError}</p>
          <button className="btn-primary mt-4" type="button" onClick={() => setRequestVersion((value) => value + 1)}>
            Try again
          </button>
        </section>
      ) : null}
      {loaded && !prerequisiteLock && !loadError ? (
        <LabRunner key={lesson.id} lesson={lesson} initialCompleted={completed} onPrerequisiteLocked={setPrerequisiteLock} />
      ) : null}
    </main>
  );
}
