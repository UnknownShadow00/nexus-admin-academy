import { useEffect, useMemo, useState } from "react";
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import ReactMarkdown from "react-markdown";
import toast from "react-hot-toast";
import Spinner from "./Spinner";
import { getLeaderboard, submitTicket, uploadScreenshots } from "../services/api";

export default function TicketSubmit({ ticket, studentId }) {
  const [writeup, setWriteup] = useState("");
  const [collaborators, setCollaborators] = useState([]);
  const [students, setStudents] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(-1);

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
    const loadingToast = toast.loading("AI is grading your work... This may take 10-15 seconds");
    const res = await submitTicket(ticket.id, {
      student_id: studentId,
      writeup,
      collaborator_ids: collaboratorIds,
      screenshots: uploadedFiles,
      grade_now: true,
    });
    toast.dismiss(loadingToast);
    setResult(res.data);
    toast.success(`Ticket graded! +${res.data?.xp_awarded} XP`);
    setLoading(false);
  };

  return (
    <section className="space-y-4">
      <article className="panel dark:bg-slate-900 dark:border-slate-700">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{ticket.title}</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{ticket.description}</p>
      </article>

      <article className="panel space-y-3 dark:bg-slate-900 dark:border-slate-700">
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

      {result ? (
        <article className="panel dark:bg-slate-900 dark:border-slate-700">
          <h3 className="text-xl font-bold">AI Score: {result.ai_score}/10 ? XP Awarded: {result.xp_awarded}</h3>
          <p className="mt-1 text-sm">Collaboration: {result.participants} people ({Math.round((result.collaboration_multiplier || 1) * 100)}% multiplier)</p>

          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <div>
              <p className="font-semibold">Strengths</p>
              <ul className="list-disc pl-5 text-sm">{(result.feedback?.strengths || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
            <div>
              <p className="font-semibold">Areas to Improve</p>
              <ul className="list-disc pl-5 text-sm">{(result.feedback?.weaknesses || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
          </div>

          <p className="mt-3 text-sm">{result.feedback?.feedback}</p>

          {result.screenshots?.length ? (
            <div className="mt-4">
              <p className="mb-2 text-sm font-semibold">Screenshots</p>
              <div className="flex flex-wrap gap-2">
                {result.screenshots.map((name, i) => {
                  const src = `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/uploads/screenshots/${name}`;
                  return <img key={name} src={src} alt={name} className="h-24 w-24 cursor-pointer rounded object-cover" onClick={() => setLightboxIndex(i)} />;
                })}
              </div>
              <Lightbox
                open={lightboxIndex >= 0}
                close={() => setLightboxIndex(-1)}
                index={lightboxIndex >= 0 ? lightboxIndex : 0}
                slides={result.screenshots.map((name) => ({ src: `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/uploads/screenshots/${name}` }))}
              />
            </div>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
