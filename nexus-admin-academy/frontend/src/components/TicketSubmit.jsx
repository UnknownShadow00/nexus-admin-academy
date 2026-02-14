import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import toast from "react-hot-toast";
import Spinner from "./Spinner";
import { getLeaderboard, submitTicket, uploadScreenshots } from "../services/api";

export default function TicketSubmit({ ticket, studentId }) {
  const navigate = useNavigate();
  const [writeup, setWriteup] = useState("");
  const [collaborators, setCollaborators] = useState([]);
  const [students, setStudents] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getLeaderboard().then((res) => setStudents((res.data || []).filter((s) => s.student_id !== studentId)));
  }, [studentId]);

  const collaboratorIds = useMemo(() => collaborators.map(Number), [collaborators]);

  const toggleCollaborator = (id, checked) => {
    setCollaborators((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) return;
    const loadingToast = toast.loading("Uploading screenshots...");
    const res = await uploadScreenshots(selectedFiles);
    toast.dismiss(loadingToast);
    setUploadedFiles(res.data?.files || []);
    toast.success("Screenshots uploaded");
  };

  const onSubmit = async () => {
    setLoading(true);
    const loadingToast = toast.loading("AI is grading your work...");
    try {
      const startedAt = Number(localStorage.getItem(`ticket_${ticket.id}_started`) || Date.now());
      const durationMinutes = Math.max(0, Math.floor((Date.now() - startedAt) / 60000));

      const res = await submitTicket(ticket.id, {
        student_id: studentId,
        writeup,
        collaborator_ids: collaboratorIds,
        screenshots: uploadedFiles,
        grade_now: true,
        duration_minutes: durationMinutes,
      });

      localStorage.removeItem(`ticket_${ticket.id}_started`);
      toast.success(`Ticket graded! +${res.data?.xp_awarded} XP`);
      navigate(`/tickets/${res.data?.submission_id}/feedback`);
    } finally {
      toast.dismiss(loadingToast);
      setLoading(false);
    }
  };

  return (
    <section className="space-y-4">
      <article className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{ticket.title}</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{ticket.description}</p>
      </article>

      <article className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <label className="text-sm font-semibold">Solution Writeup (Markdown supported)</label>
        <textarea className="input-field h-40" value={writeup} onChange={(e) => setWriteup(e.target.value)} placeholder="Describe troubleshooting steps..." />

        <label className="text-sm font-semibold">Upload Screenshots (optional)</label>
        <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))} />
        <button className="btn-secondary" type="button" onClick={handleUpload}>Upload Selected</button>

        <label className="text-sm font-semibold">Collaborators (optional)</label>
        <div className="grid gap-2 md:grid-cols-2">
          {students.map((student) => (
            <label key={student.student_id} className="flex items-center gap-2 rounded border border-slate-200 p-2 dark:border-slate-700">
              <input type="checkbox" checked={collaborators.includes(student.student_id)} onChange={(e) => toggleCollaborator(student.student_id, e.target.checked)} />
              {student.name}
            </label>
          ))}
        </div>

        <button className="btn-primary" disabled={loading || !writeup.trim()} onClick={onSubmit}>
          {loading ? <Spinner size="sm" text="Submitting..." /> : "Submit Solution"}
        </button>

        <div className="rounded border border-slate-200 p-3 dark:border-slate-700">
          <p className="mb-2 text-sm font-semibold">Markdown Preview</p>
          <ReactMarkdown>{writeup || "_Your preview will appear here._"}</ReactMarkdown>
        </div>
      </article>
    </section>
  );
}
