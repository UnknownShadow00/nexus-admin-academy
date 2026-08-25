import { useCallback, useEffect, useMemo, useState } from "react";
import BackLink from "../components/BackLink";
import Spinner from "../components/Spinner";
import Banner from "../components/ui/Banner";
import PageHeader from "../components/ui/PageHeader";
import {
  attemptFinalShiftIncident,
  getFinalShift,
  openFinalShiftIncident,
  startFinalShift,
  submitFinalShiftHandoff,
} from "../services/api";

const STATUS_LABEL = {
  not_started: "Not opened yet",
  investigating: "Investigating",
  resolved: "Resolved",
  escalated: "Escalated",
};

function StatusPill({ status }) {
  const label = STATUS_LABEL[status] || "Not opened yet";
  const cls =
    status === "resolved" || status === "escalated"
      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
      : status === "investigating"
        ? "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300"
        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{label}</span>;
}

function IncidentCard({ incident, onOpen }) {
  return (
    <button
      className="panel w-full min-w-0 space-y-2 text-left transition hover:border-blue-400 dark:border-slate-700 dark:bg-slate-900"
      onClick={() => onOpen(incident.key)}
      type="button"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{incident.requester}</span>
        <StatusPill status={incident.state.status} />
      </div>
      <p className="text-xs text-slate-400 dark:text-slate-500">Reported {incident.reported_at}</p>
      <p className="text-sm text-slate-600 dark:text-slate-300">{incident.complaint}</p>
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{incident.impact_clue}</p>
    </button>
  );
}

function EvidencePanel({ panel, inspected, onToggle }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700">
      <button
        aria-expanded={inspected}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium text-slate-700 dark:text-slate-200"
        onClick={() => onToggle(panel.id)}
        type="button"
      >
        <span>{panel.label}</span>
        <span className="text-xs text-slate-400">{inspected ? "Inspected — hide" : "Inspect"}</span>
      </button>
      {inspected ? (
        <dl className="space-y-1 border-t border-slate-200 px-3 py-2 dark:border-slate-700">
          {panel.fields.map((field) => (
            <div className="flex flex-col text-sm sm:flex-row sm:gap-2" key={field.label}>
              <dt className="min-w-[9rem] font-medium text-slate-500 dark:text-slate-400">{field.label}</dt>
              <dd className="text-slate-700 dark:text-slate-200">{field.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

function IncidentDetail({ incident, labId, onBack, onChanged }) {
  const [inspected, setInspected] = useState(new Set(incident.state.inspected_panel_ids || []));
  const [diagnosis, setDiagnosis] = useState(incident.state.diagnosis_answer || "");
  const [action, setAction] = useState(incident.state.action_choice || "");
  const [documentation, setDocumentation] = useState(incident.state.documentation || {});
  const [message, setMessage] = useState("");
  const [ready, setReady] = useState(incident.state.status === "resolved" || incident.state.status === "escalated");
  const [verification, setVerification] = useState(incident.state.verification || null);
  const [busy, setBusy] = useState(false);

  function togglePanel(panelId) {
    setInspected((prev) => {
      const next = new Set(prev);
      if (next.has(panelId)) next.delete(panelId);
      else next.add(panelId);
      return next;
    });
  }

  function setDoc(field, value) {
    setDocumentation((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCheckPlan() {
    setBusy(true);
    setMessage("");
    try {
      const res = await attemptFinalShiftIncident(labId, incident.key, {
        inspected_panel_ids: Array.from(inspected),
        diagnosis_answer: diagnosis || null,
        action_choice: action || null,
        documentation,
      });
      const data = res.data;
      setReady(data.ready);
      setVerification(data.verification);
      setMessage(data.message);
      onChanged();
    } catch (err) {
      setMessage(err?.userMessage || "Could not check this plan. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const docFields = [
    { id: "issue", label: "Issue" },
    { id: "evidence", label: "Evidence" },
    { id: "action", label: "Action taken" },
    { id: "verification", label: "Verification" },
    ...(incident.requires_user_update ? [{ id: "user_update", label: "User update" }] : []),
    ...(incident.requires_escalation ? [{ id: "escalation", label: "Escalation note" }] : []),
  ];

  return (
    <div className="space-y-4">
      <button className="text-sm text-blue-500 hover:underline" onClick={onBack} type="button">
        ← Back to queue
      </button>

      <div className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{incident.requester}</h2>
          <StatusPill status={incident.state.status} />
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-300">{incident.complaint}</p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{incident.impact_clue}</p>
      </div>

      <div className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Evidence</h3>
        <div className="space-y-2">
          {incident.panels.map((panel) => (
            <EvidencePanel inspected={inspected.has(panel.id)} key={panel.id} onToggle={togglePanel} panel={panel} />
          ))}
        </div>
      </div>

      <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Diagnosis</h3>
        <div className="space-y-2">
          {incident.diagnosis_options.map((option) => (
            <label className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200" key={option.id}>
              <input
                checked={diagnosis === option.id}
                name={`diagnosis-${incident.key}`}
                onChange={() => setDiagnosis(option.id)}
                type="radio"
                value={option.id}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Action</h3>
        <div className="space-y-2">
          {incident.actions.map((option) => (
            <label className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200" key={option.id}>
              <input
                checked={action === option.id}
                name={`action-${incident.key}`}
                onChange={() => setAction(option.id)}
                type="radio"
                value={option.id}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Documentation</h3>
        {docFields.map((field) => (
          <label className="block space-y-1 text-sm" key={field.id}>
            <span className="font-medium text-slate-600 dark:text-slate-300">{field.label}</span>
            <textarea
              className="input-field min-h-[3rem] w-full"
              onChange={(event) => setDoc(field.id, event.target.value)}
              value={documentation[field.id] || ""}
            />
          </label>
        ))}
      </div>

      {message ? (
        ready ? (
          <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200">
            Ready: {message}
          </div>
        ) : (
          <Banner variant="info">{message}</Banner>
        )
      ) : null}

      {ready && verification ? (
        <div className="panel space-y-2 border-emerald-300 dark:border-emerald-800 dark:bg-slate-900">
          <h3 className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">{verification.label}</h3>
          <dl className="space-y-1">
            {verification.fields.map((field) => (
              <div className="flex flex-col text-sm sm:flex-row sm:gap-2" key={field.label}>
                <dt className="min-w-[9rem] font-medium text-slate-500 dark:text-slate-400">{field.label}</dt>
                <dd className="text-slate-700 dark:text-slate-200">{field.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      <button className="btn-primary w-full" disabled={busy} onClick={handleCheckPlan} type="button">
        {busy ? "Checking..." : "Check my plan"}
      </button>
    </div>
  );
}

function HandoffForm({ labId, incidents, onSubmitted }) {
  const [resolved, setResolved] = useState("");
  const [escalated, setEscalated] = useState("");
  const [watchItems, setWatchItems] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const unfinished = incidents.filter(
    (incident) => incident.state.status !== "resolved" && incident.state.status !== "escalated"
  );

  async function handleSubmit() {
    setBusy(true);
    setError("");
    try {
      const res = await submitFinalShiftHandoff(labId, { resolved, escalated, watch_items: watchItems });
      onSubmitted(res.data.grading);
    } catch (err) {
      setError(err?.userMessage || "Could not submit the handoff. Every incident must be resolved or escalated first.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Final handoff</h2>
      {unfinished.length > 0 ? (
        <Banner variant="info">
          Still open: {unfinished.map((incident) => incident.requester).join(", ")}. Finish every incident before handing off.
        </Banner>
      ) : null}
      <label className="block space-y-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">Resolved</span>
        <textarea className="input-field min-h-[3rem] w-full" onChange={(event) => setResolved(event.target.value)} value={resolved} />
      </label>
      <label className="block space-y-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">Escalated</span>
        <textarea className="input-field min-h-[3rem] w-full" onChange={(event) => setEscalated(event.target.value)} value={escalated} />
      </label>
      <label className="block space-y-1 text-sm">
        <span className="font-medium text-slate-600 dark:text-slate-300">Watch items</span>
        <textarea className="input-field min-h-[3rem] w-full" onChange={(event) => setWatchItems(event.target.value)} value={watchItems} />
      </label>
      {error ? <Banner variant="error">{error}</Banner> : null}
      <button className="btn-primary w-full" disabled={busy || unfinished.length > 0} onClick={handleSubmit} type="button">
        {busy ? "Submitting..." : "Submit handoff"}
      </button>
    </div>
  );
}

function GradingResult({ grading }) {
  return (
    <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
      {grading.passed ? (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200">
          Passed — overall score {grading.overall_score}%
        </div>
      ) : (
        <Banner variant="error">Not yet passing — overall score {grading.overall_score}%</Banner>
      )}
      <p className="text-sm text-slate-600 dark:text-slate-300">{grading.feedback_summary}</p>
      <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
        {Object.entries(grading.dimension_scores).map(([dimension, score]) => (
          <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950" key={dimension}>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {dimension.replaceAll("_", " ")}
            </dt>
            <dd className="text-sm font-semibold text-slate-700 dark:text-slate-200">{score}%</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function FinalSupportShiftPage({ labId }) {
  const [shift, setShift] = useState(null);
  const [error, setError] = useState("");
  const [selectedKey, setSelectedKey] = useState(null);
  const [grading, setGrading] = useState(null);
  const [starting, setStarting] = useState(false);

  const load = useCallback(() => {
    getFinalShift(labId, { suppressToast: true })
      .then((res) => setShift(res.data))
      .catch((err) => setError(err?.userMessage || "Could not load the final shift."));
  }, [labId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (shift?.grading) setGrading(shift.grading);
  }, [shift]);

  async function handleStart() {
    setStarting(true);
    try {
      await startFinalShift(labId);
      load();
    } catch (err) {
      setError(err?.userMessage || "Could not start the final shift.");
    } finally {
      setStarting(false);
    }
  }

  async function handleOpenIncident(key) {
    try {
      await openFinalShiftIncident(labId, key);
    } catch {
      // Non-fatal: the incident still opens locally even if the order log fails to save.
    }
    setSelectedKey(key);
    load();
  }

  const selectedIncident = useMemo(
    () => shift?.incidents.find((incident) => incident.key === selectedKey) || null,
    [shift, selectedKey]
  );

  if (error) {
    return <main className="mx-auto max-w-4xl p-6 text-sm text-slate-500 dark:text-slate-300">{error}</main>;
  }
  if (!shift) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <Spinner text="Loading final shift..." />
      </main>
    );
  }

  const allDone = shift.incidents.every(
    (incident) => incident.state.status === "resolved" || incident.state.status === "escalated"
  );

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <BackLink fallbackLabel="Guided Labs" fallbackTo="/labs" />
      <PageHeader subtitle={shift.queue_intro} title={shift.title} />

      {shift.guidance_notes?.length > 0 ? (
        <div className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">How this works</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            {shift.guidance_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {shift.status === "not_started" ? (
        <div className="panel space-y-3 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-sm text-slate-600 dark:text-slate-300">Three issues are waiting. Begin the shift to see the queue.</p>
          <button className="btn-primary" disabled={starting} onClick={handleStart} type="button">
            {starting ? "Starting..." : "Begin final shift"}
          </button>
        </div>
      ) : grading ? (
        <GradingResult grading={grading} />
      ) : selectedIncident ? (
        <IncidentDetail incident={selectedIncident} labId={labId} onBack={() => setSelectedKey(null)} onChanged={load} />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {shift.incidents.map((incident) => (
              <IncidentCard incident={incident} key={incident.key} onOpen={handleOpenIncident} />
            ))}
          </div>
          {allDone ? <HandoffForm incidents={shift.incidents} labId={labId} onSubmitted={setGrading} /> : null}
        </div>
      )}
    </main>
  );
}
