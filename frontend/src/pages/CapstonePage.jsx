import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Spinner from "../components/Spinner";
import PrerequisiteLock, { getPrerequisiteLock } from "../components/PrerequisiteLock";
import PageHeader from "../components/ui/PageHeader";
import { getCapstone, startCapstone, submitCapstone } from "../services/api";

const statusConfig = {
  not_started: { label: "Not Started", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  in_progress: { label: "In Progress", cls: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" },
  submitted: { label: "Submitted", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" },
};

export default function CapstonePage() {
  const { capstoneId } = useParams();
  const [capstone, setCapstone] = useState(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [prerequisiteLock, setPrerequisiteLock] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getCapstone(capstoneId, { suppressToast: true })
      .then((res) => {
        if (cancelled) return;
        setCapstone(res.data);
        setNotes(res.data?.notes || "");
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.userMessage || "Unable to load capstone.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [capstoneId]);

  async function handleStart() {
    setBusy(true);
    try {
      const res = await startCapstone(capstoneId);
      setCapstone(res.data);
      setNotes(res.data?.notes || "");
    } catch (err) {
      setPrerequisiteLock(getPrerequisiteLock(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit() {
    setBusy(true);
    try {
      const res = await submitCapstone(capstoneId, { notes });
      setCapstone(res.data);
      setNotes(res.data?.notes || "");
    } catch (err) {
      setPrerequisiteLock(getPrerequisiteLock(err));
    } finally {
      setBusy(false);
    }
  }

  if (!capstone && !error) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <Spinner text="Loading capstone..." />
      </main>
    );
  }

  if (error) {
    return <main className="mx-auto max-w-4xl p-6 text-sm text-slate-500 dark:text-slate-300">{error}</main>;
  }

  const requirements = Array.isArray(capstone.requirements?.skills) ? capstone.requirements.skills : [];
  const deliverables = Array.isArray(capstone.deliverables?.items) ? capstone.deliverables.items : [];
  const rubric = Object.entries(capstone.rubric || {});
  const status = statusConfig[capstone.status] || statusConfig.not_started;

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <PageHeader
        title={capstone.title}
        subtitle={`Week ${capstone.week_number} | ${capstone.estimated_hours} hours`}
      />

      <PrerequisiteLock lock={prerequisiteLock} />

      <div className="grid gap-6 lg:grid-cols-2">
        <article className="space-y-4">
          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <p className="text-sm text-slate-600 dark:text-slate-300">{capstone.description}</p>
          </div>

          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Requirements</h2>
            <ul className="space-y-2">
              {requirements.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                  <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-blue-500" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Deliverables</h2>
            <ul className="space-y-2">
              {deliverables.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                  <span className="mt-0.5 flex h-4 w-4 items-center justify-center rounded border border-slate-300 text-[10px] dark:border-slate-600">
                    ✓
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Rubric</h2>
            <ul className="space-y-3">
              {rubric.map(([key, value]) => (
                <li key={key} className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                  <div className="font-medium capitalize text-slate-700 dark:text-slate-200">{key.replaceAll("_", " ")}</div>
                  <p>{value}</p>
                </li>
              ))}
            </ul>
          </div>
        </article>

        <aside className="panel h-fit space-y-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Your Submission</h2>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${status.cls}`}>{status.label}</span>
          </div>

          <textarea
            className="input-field min-h-64 w-full"
            placeholder="Document your capstone approach, findings, deliverables, and reflection here."
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            readOnly={Boolean(prerequisiteLock) || busy || capstone.status === "submitted"}
          />

          {!prerequisiteLock ? (
            <div className="flex flex-wrap gap-3">
              {capstone.status === "not_started" ? (
                <button className="btn-secondary" onClick={handleStart} disabled={busy} type="button">
                  {busy ? "Starting..." : "Start Capstone"}
                </button>
              ) : null}
              <button
                className="btn-primary"
                onClick={handleSubmit}
                disabled={busy || capstone.status === "submitted"}
                type="button"
              >
                {capstone.status === "submitted" ? "Submitted" : busy ? "Submitting..." : "Submit Capstone"}
              </button>
            </div>
          ) : null}

          <div className="text-xs text-slate-500 dark:text-slate-400">
            {capstone.status === "submitted"
              ? "This capstone has been submitted."
              : "Start the capstone to mark it in progress, then submit your notes when finished."}
          </div>
        </aside>
      </div>
    </main>
  );
}
