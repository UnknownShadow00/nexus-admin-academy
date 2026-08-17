import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import EmptyState from "../components/EmptyState";
import PrerequisiteLock from "../components/PrerequisiteLock";
import PageHeader from "../components/ui/PageHeader";
import LabRunner from "../features/cli-labs/components/LabRunner";
import { findCliLesson, nextCliLesson } from "../features/cli-labs/data/lessonCatalog";
import { getCliLab } from "../services/api";

export default function CliLabPage() {
  const { labId } = useParams();
  const lesson = findCliLesson(labId);
  const nextLesson = nextCliLesson(labId);
  const [completed, setCompleted] = useState(false);
  const [prerequisiteLock, setPrerequisiteLock] = useState(null);

  useEffect(() => {
    if (!labId) return;
    let cancelled = false;
    getCliLab(labId, { suppressToast: true })
      .then((response) => {
        if (!cancelled) setCompleted(Boolean(response.data?.completed));
      })
      .catch(() => {
        if (!cancelled) setCompleted(false);
      });
    return () => {
      cancelled = true;
    };
  }, [labId]);

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
      <LabRunner key={lesson.id} lesson={lesson} initialCompleted={completed} onPrerequisiteLocked={setPrerequisiteLock} />
    </main>
  );
}
