import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import Spinner from "../components/Spinner";
import PrerequisiteLock, { getPrerequisiteLock } from "../components/PrerequisiteLock";
import EndpointEvidenceWorkbench from "../components/EndpointEvidenceWorkbench";
import EvidenceCaseWorkbench from "../components/EvidenceCaseWorkbench";
import StructuredLabExercise from "../components/StructuredLabExercise";
import FinalSupportShiftPage from "./FinalSupportShiftPage";
import { DifficultyBadge } from "../components/ui/Badge";
import Banner from "../components/ui/Banner";
import PageHeader from "../components/ui/PageHeader";
import { createLabVmAccess, getLab, getLabVmStatus, startLab, submitLab, uploadLabEvidence, verifyEvidenceLab } from "../services/api";
import { setMonitoringContext } from "../monitoring/sentry";

const provisioningStatuses = new Set(["provisioning", "starting", "waiting_for_ip", "configuring_connection"]);

const statusConfig = {
  not_started: { label: "Not Started", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  assigned: { label: "Assigned", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  in_progress: { label: "In Progress", cls: "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" },
  submitted: { label: "Submitted", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" },
};

export default function LabPage() {
  const { labId } = useParams();
  const [lab, setLab] = useState(null);
  const [guacUrl, setGuacUrl] = useState(null);
  const [vmAssignment, setVmAssignment] = useState(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [vmError, setVmError] = useState("");
  const [busy, setBusy] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState(null);
  const [evidenceArtifacts, setEvidenceArtifacts] = useState([]);
  const [evidenceMessage, setEvidenceMessage] = useState("");
  const [evidenceBusy, setEvidenceBusy] = useState(false);
  const [evidenceInputKey, setEvidenceInputKey] = useState(0);
  const [prerequisiteLock, setPrerequisiteLock] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getLab(labId, { suppressToast: true })
      .then((res) => {
        if (cancelled) return;
        setLab(res.data);
        setNotes(res.data?.notes || "");
        setEvidenceArtifacts(res.data?.evidence_artifacts || []);
        setVmAssignment(res.data?.vm_assignment || null);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.userMessage || "Unable to load lab.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [labId]);

  useEffect(() => {
    if (!lab) return;
    setMonitoringContext({
      nexus_area: lab.lab_type === "structured_final_shift" ? "final_shift" : "lab",
      training_week: lab.week_number,
      lab_template_id: labId,
      module_name: lab.title,
      activity_type: lab.lab_type,
    });
  }, [lab, labId]);

  useEffect(() => {
    if (!vmAssignment || !provisioningStatuses.has(vmAssignment.status)) return undefined;
    let cancelled = false;
    const timer = window.setInterval(() => {
      getLabVmStatus(labId, { suppressToast: true })
        .then((res) => {
          if (!cancelled) setVmAssignment(res.data);
        })
        .catch(() => {
          if (!cancelled) setVmError("Unable to check the lab environment status.");
        });
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [labId, vmAssignment?.status]);

  useEffect(() => {
    if (vmAssignment?.status !== "running" || guacUrl) return;
    let cancelled = false;
    createLabVmAccess(labId, { suppressToast: true })
      .then((res) => {
        if (!cancelled) setGuacUrl(res.data?.url || null);
      })
      .catch((err) => {
        if (!cancelled) setVmError(err?.userMessage || "Unable to open the remote lab session.");
      });
    return () => {
      cancelled = true;
    };
  }, [guacUrl, labId, vmAssignment?.status]);

  async function handleStart() {
    setBusy(true);
    setVmError("");
    try {
      const res = await startLab(labId);
      setLab(res.data);
      setNotes(res.data?.notes || "");
      setEvidenceArtifacts(res.data?.evidence_artifacts || []);
      setVmAssignment(res.data?.vm_assignment || null);
    } catch (err) {
      const lock = getPrerequisiteLock(err);
      if (lock) setPrerequisiteLock(lock);
      else setVmError(err?.userMessage || "Unable to start the lab environment.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit() {
    setBusy(true);
    try {
      const res = await submitLab(labId, { notes });
      setLab(res.data);
      setNotes(res.data?.notes || "");
      setVmAssignment(null);
      setGuacUrl(null);
    } catch (err) {
      const lock = getPrerequisiteLock(err);
      if (lock) setPrerequisiteLock(lock);
      else setVmError(err?.userMessage || "Unable to submit the lab.");
    } finally {
      setBusy(false);
    }
  }

  async function handleStructuredSubmit(answers, terminalSession = "") {
    setBusy(true);
    try {
      const res = await submitLab(labId, { notes: terminalSession, answers });
      setLab(res.data);
      setVmAssignment(null);
      setGuacUrl(null);
    } catch (err) {
      const lock = getPrerequisiteLock(err);
      if (lock) setPrerequisiteLock(lock);
      else setVmError(err?.userMessage || "Unable to submit your answers.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEvidenceVerify(answers, inspectedPanelIds) {
    setBusy(true);
    try {
      const res = await verifyEvidenceLab(labId, answers, inspectedPanelIds);
      return res.data;
    } catch (err) {
      const lock = getPrerequisiteLock(err);
      if (lock) setPrerequisiteLock(lock);
      else setVmError(err?.userMessage || "Unable to verify the simulated outcome.");
      return { ready: false, message: "Verification could not be completed." };
    } finally {
      setBusy(false);
    }
  }

  async function handleEvidenceUpload() {
    if (!evidenceFile || !lab?.run_id) return;
    setEvidenceBusy(true);
    setEvidenceMessage("");
    try {
      const res = await uploadLabEvidence(lab.run_id, evidenceFile);
      const artifact = {
        artifact_id: res.data?.artifact_id,
        storage_key: res.data?.storage_key,
        original_filename: evidenceFile.name,
      };
      setEvidenceArtifacts((items) => [artifact, ...items]);
      setEvidenceFile(null);
      setEvidenceInputKey((key) => key + 1);
      setEvidenceMessage("Screenshot uploaded");
    } catch (err) {
      const lock = getPrerequisiteLock(err);
      if (lock) setPrerequisiteLock(lock);
      else setEvidenceMessage(err?.userMessage || "Unable to upload evidence.");
    } finally {
      setEvidenceBusy(false);
    }
  }

  if (!lab && !error) {
    return (
      <main className="mx-auto max-w-4xl p-6">
        <Spinner text="Loading lab..." />
      </main>
    );
  }

  if (error) {
    return <main className="mx-auto max-w-4xl p-6 text-sm text-slate-500 dark:text-slate-300">{error}</main>;
  }

  if (lab.lab_type === "structured_final_shift") {
    return <FinalSupportShiftPage labId={labId} />;
  }

  const tasks = Array.isArray(lab.success_criteria?.tasks) ? lab.success_criteria.tasks : [];
  const hints = Array.isArray(lab.hints) ? lab.hints : [];
  const status = statusConfig[lab.status] || statusConfig.not_started;
  const isStructured = typeof lab.lab_type === "string" && lab.lab_type.startsWith("structured_");
  const structuredQuestions = isStructured ? lab.success_criteria?.questions : null;
  const requiresEvidence = Object.keys(lab.required_evidence?.evidence_types || lab.required_evidence || {}).length > 0;
  const canUploadEvidence =
    requiresEvidence && ["in_progress", "assigned"].includes(lab.status) && Boolean(lab.run_id);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <BackLink fallbackLabel="Guided Labs" fallbackTo="/labs" />
      <PageHeader
        title={lab.title}
        subtitle={`Week ${lab.week_number} | ${lab.estimated_minutes} minutes | ${lab.lab_type}`}
        actions={<DifficultyBadge level={lab.difficulty} />}
      />

      <PrerequisiteLock lock={prerequisiteLock} />

      {vmError ? <Banner variant="error">{vmError}</Banner> : null}

      {vmAssignment && provisioningStatuses.has(vmAssignment.status) ? (
        <Banner variant="info">Preparing the lab environment: {vmAssignment.status.replaceAll("_", " ")}…</Banner>
      ) : null}
      {vmAssignment?.status === "failed" ? (
        <Banner variant="error">{vmAssignment.provisioning_error || "Lab environment provisioning failed."}</Banner>
      ) : null}

      {guacUrl ? (
        <div className="panel overflow-hidden dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Lab Environment</h2>
            <a className="text-xs text-blue-500 hover:underline" href={guacUrl} rel="noopener noreferrer" target="_blank">
              Open in new tab
            </a>
          </div>
          <iframe
            allowFullScreen
            className="h-[60vh] w-full rounded-lg border border-slate-200 dark:border-slate-700"
            src={guacUrl}
            title="Lab VM"
          />
        </div>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <article className="min-w-0 space-y-4 self-start lg:sticky lg:top-20">
          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Scenario</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">{lab.description}</p>
          </div>

          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Task and environment</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">{lab.setup_instructions}</p>
          </div>

          {canUploadEvidence && !prerequisiteLock ? (
            <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Evidence Upload</h2>
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  key={evidenceInputKey}
                  accept="image/*"
                  className="input-field"
                  onChange={(event) => setEvidenceFile(event.target.files?.[0] || null)}
                  type="file"
                />
                <button className="btn-secondary shrink-0" disabled={!evidenceFile || evidenceBusy} onClick={handleEvidenceUpload} type="button">
                  {evidenceBusy ? "Uploading..." : "Upload Screenshot"}
                </button>
              </div>
              {evidenceMessage ? <p className="text-sm font-medium text-emerald-600 dark:text-emerald-300">{evidenceMessage}</p> : null}
              {evidenceArtifacts.length ? (
                <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                  {evidenceArtifacts.map((artifact) => (
                    <li key={artifact.artifact_id || artifact.id || artifact.storage_key} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950">
                      {artifact.original_filename || artifact.storage_key}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {tasks.length > 0 ? (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Verify</h2>
              <ul className="space-y-2">
                {tasks.map((task) => (
                  <li key={task} className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                    <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-blue-500" />
                    <span>{task}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {hints.length > 0 ? (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Hints</h2>
              <ul className="space-y-2">
                {hints.map((hint) => (
                  <li key={hint} className="text-sm text-slate-600 dark:text-slate-300">
                    {hint}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>

        <aside className="panel min-w-0 h-fit space-y-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {isStructured ? "Answer the exercise" : "Work and explain"}
            </h2>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${status.cls}`}>{status.label}</span>
          </div>

          {lab.success_criteria?.evidence_case_workbench ? (
            <EvidenceCaseWorkbench
              key={`evidence-case-${lab.id}`}
              workbench={lab.success_criteria.evidence_case_workbench}
              questions={structuredQuestions}
              feedback={lab.structured_feedback}
              initialNotes={lab.notes}
              submitted={lab.status === "submitted" && (lab.structured_feedback?.score_pct ?? 0) >= 70}
              busy={busy}
              onVerify={handleEvidenceVerify}
              onSubmit={handleStructuredSubmit}
            />
          ) : lab.success_criteria?.endpoint_workbench ? (
            <EndpointEvidenceWorkbench
              key={`endpoint-evidence-${lab.id}`}
              workbench={lab.success_criteria.endpoint_workbench}
              questions={structuredQuestions}
              feedback={lab.structured_feedback}
              initialNotes={lab.notes}
              submitted={lab.status === "submitted" && (lab.structured_feedback?.score_pct ?? 0) >= 70}
              busy={busy}
              onVerify={handleEvidenceVerify}
              onSubmit={handleStructuredSubmit}
            />
          ) : isStructured ? (
            <StructuredLabExercise
              questions={structuredQuestions}
              requiredCommands={lab.success_criteria?.required_commands}
              terminalProfile={lab.success_criteria?.terminal_profile}
              feedback={lab.structured_feedback}
              submitted={lab.status === "submitted" && (lab.structured_feedback?.score_pct ?? 0) >= 70}
              busy={busy}
              onSubmit={handleStructuredSubmit}
            />
          ) : (
            <>
              <textarea
                className="input-field min-h-64 w-full"
                placeholder="Record your evidence, diagnosis, work, and verification. When useful, end with one sentence: What caused the problem?"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                readOnly={Boolean(prerequisiteLock) || busy || lab.status === "submitted"}
              />

              {!prerequisiteLock ? (
                <div className="flex flex-wrap gap-3">
                  {["not_started", "assigned"].includes(lab.status) ? (
                    <button className="btn-secondary" onClick={handleStart} disabled={busy} type="button">
                      {busy ? "Starting..." : "Start Lab"}
                    </button>
                  ) : null}
                  <button className="btn-primary" onClick={handleSubmit} disabled={busy || lab.status === "submitted"} type="button">
                    {lab.status === "submitted" ? "Submitted" : busy ? "Submitting..." : "Submit Lab"}
                  </button>
                </div>
              ) : null}

              <div className="text-xs text-slate-500 dark:text-slate-400">
                {lab.status === "submitted"
                  ? "This lab has been submitted."
                  : "Start the lab to mark it in progress, then submit your notes when finished."}
              </div>
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
