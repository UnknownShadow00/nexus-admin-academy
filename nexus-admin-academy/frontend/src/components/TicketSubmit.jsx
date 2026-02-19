import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import toast from "react-hot-toast";
import EvidenceUploader from "./EvidenceUploader";
import Spinner from "./Spinner";
import { getStudents, submitTicket, uploadScreenshots } from "../services/api";

export default function TicketSubmit({ ticket, studentId }) {
  const navigate = useNavigate();
  const draftKey = `ticket_draft_${ticket.id}_${studentId}`;
  const [symptom, setSymptom] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [resolution, setResolution] = useState("");
  const [verification, setVerification] = useState("");
  const [commandsUsed, setCommandsUsed] = useState("");
  const [collaborators, setCollaborators] = useState([]);
  const [students, setStudents] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [evidenceUploads, setEvidenceUploads] = useState([]);

  useEffect(() => {
    getStudents().then((res) => setStudents((res.data || []).filter((s) => s.id !== studentId)));
  }, [studentId]);

  useEffect(() => {
    const raw = localStorage.getItem(draftKey);
    if (!raw) return;
    try {
      const draft = JSON.parse(raw);
      setSymptom(draft.symptom || "");
      setRootCause(draft.rootCause || "");
      setResolution(draft.resolution || "");
      setVerification(draft.verification || "");
      setCommandsUsed(draft.commandsUsed || "");
    } catch {
      // Ignore invalid draft payloads.
    }
  }, [draftKey]);

  useEffect(() => {
    const timer = setInterval(() => {
      const payload = {
        symptom,
        rootCause,
        resolution,
        verification,
        commandsUsed,
      };
      localStorage.setItem(draftKey, JSON.stringify(payload));
    }, 10000);
    return () => clearInterval(timer);
  }, [draftKey, symptom, rootCause, resolution, verification, commandsUsed]);

  const collaboratorIds = useMemo(() => collaborators.map(Number), [collaborators]);
  const writeup = useMemo(
    () =>
      `Symptom:\n${symptom}\n\nRoot Cause:\n${rootCause}\n\nResolution:\n${resolution}\n\nVerification:\n${verification}`,
    [symptom, rootCause, resolution, verification]
  );
  const canSubmit = symptom.trim() && rootCause.trim() && resolution.trim() && verification.trim();

  const toggleCollaborator = (id, checked) => {
    setCollaborators((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) return;
    const loadingToast = toast.loading("Uploading screenshots...");
    await uploadScreenshots(selectedFiles);
    toast.dismiss(loadingToast);
    toast.success("Screenshots uploaded");
  };

  const onSubmit = async () => {
    setLoading(true);
    const loadingToast = toast.loading("AI is grading your work...");
    try {
      const startedAt = Number(localStorage.getItem(`ticket_${ticket.id}_started`) || Date.now());
      const durationMinutes = Math.max(0, Math.floor((Date.now() - startedAt) / 60000));

      const validArtifacts = evidenceUploads.filter((x) => x.validation?.valid && x.artifact_id);
      const screenshotArtifacts = validArtifacts.filter((x) => x.type === "screenshot");
      const beforeId = screenshotArtifacts[0]?.artifact_id || null;
      const afterId = screenshotArtifacts[1]?.artifact_id || null;

      const res = await submitTicket(ticket.id, {
        student_id: studentId,
        symptom,
        root_cause: rootCause,
        resolution,
        verification,
        commands_used: commandsUsed,
        writeup,
        collaborator_ids: collaboratorIds,
        before_screenshot_id: beforeId,
        after_screenshot_id: afterId,
        grade_now: true,
        duration_minutes: durationMinutes,
      });

      localStorage.removeItem(`ticket_${ticket.id}_started`);
      localStorage.removeItem(draftKey);
      toast.success("Ticket graded and queued for instructor verification");
      navigate(`/tickets/${res.data?.submission_id}/feedback`);
    } finally {
      toast.dismiss(loadingToast);
      setLoading(false);
    }
  };

  return (
    <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="text-xl font-bold">ITIL Documentation Editor</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        All sections are required: Symptom, Root Cause, Resolution, Verification.
      </p>

      <div className="grid gap-4">
        <div>
          <label className="text-sm font-semibold">Symptom</label>
          <textarea className="input-field h-24" value={symptom} onChange={(e) => setSymptom(e.target.value)} placeholder="Describe what the user reported and impact." />
        </div>
        <div>
          <label className="text-sm font-semibold">Root Cause</label>
          <textarea className="input-field h-24" value={rootCause} onChange={(e) => setRootCause(e.target.value)} placeholder="Explain identified root cause." />
        </div>
        <div>
          <label className="text-sm font-semibold">Resolution</label>
          <textarea className="input-field h-24" value={resolution} onChange={(e) => setResolution(e.target.value)} placeholder="Document remediation steps taken." />
        </div>
        <div>
          <label className="text-sm font-semibold">Verification</label>
          <textarea className="input-field h-24" value={verification} onChange={(e) => setVerification(e.target.value)} placeholder="Confirm how the fix was validated." />
        </div>
        <div>
          <label className="text-sm font-semibold">Commands Used</label>
          <textarea className="input-field h-24" value={commandsUsed} onChange={(e) => setCommandsUsed(e.target.value)} placeholder="Paste the commands you ran." />
          <button
            className="btn-secondary mt-2"
            type="button"
            onClick={() => setCommandsUsed(localStorage.getItem("terminal_session_history") || "")}
          >
            Copy from Terminal
          </button>
          <p className="mt-1 text-xs text-slate-500">Draft auto-saved.</p>
        </div>
      </div>

      <label className="text-sm font-semibold">Upload Screenshots (optional legacy upload)</label>
      <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))} />
      <button className="btn-secondary" type="button" onClick={handleUpload}>Upload Selected</button>

      <EvidenceUploader
        ticketId={ticket.id}
        requiredEvidence={(ticket.required_evidence?.evidence_types || []).map((e) => ({ type: e.type, description: e.description, ...(e.validation || {}) }))}
        onComplete={setEvidenceUploads}
      />

      <label className="text-sm font-semibold">Collaborators (optional)</label>
      <div className="grid gap-2 md:grid-cols-2">
        {students.map((student) => (
          <label key={student.id} className="flex items-center gap-2 rounded border border-slate-200 p-2 dark:border-slate-700">
            <input type="checkbox" checked={collaborators.includes(student.id)} onChange={(e) => toggleCollaborator(student.id, e.target.checked)} />
            {student.name}
          </label>
        ))}
      </div>

      <button className="btn-primary" disabled={loading || !canSubmit} onClick={onSubmit}>
        {loading ? <Spinner size="sm" text="Submitting..." /> : "Submit for Instructor Verification"}
      </button>

      <div className="rounded border border-slate-200 p-3 dark:border-slate-700">
        <p className="mb-2 text-sm font-semibold">Markdown Preview</p>
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown>{canSubmit ? writeup : "_Preview appears when all ITIL sections are filled._"}</ReactMarkdown>
        </div>
      </div>
    </section>
  );
}
