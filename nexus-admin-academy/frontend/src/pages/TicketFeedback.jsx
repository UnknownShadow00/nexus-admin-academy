import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, CheckCircle, MessageSquare } from "lucide-react";
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { getSubmission } from "../services/api";

export default function TicketFeedback() {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxIndex, setLightboxIndex] = useState(-1);

  useEffect(() => {
    const run = async () => {
      try {
        const response = await getSubmission(submissionId);
        setSubmission(response.data || null);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [submissionId]);

  if (loading) return <main className="mx-auto max-w-4xl p-6">Loading feedback...</main>;
  if (!submission) return <main className="mx-auto max-w-4xl p-6">Submission not found</main>;

  const feedback = typeof submission.ai_feedback === "string" ? JSON.parse(submission.ai_feedback) : (submission.ai_feedback || {});
  const images = (submission.evidence_artifacts || [])
    .filter((a) => a.artifact_type === "screenshot")
    .map((a) => `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/uploads/screenshots/${a.storage_key}`);

  return (
    <main className="mx-auto max-w-4xl p-6">
      <button onClick={() => navigate("/tickets")} className="mb-6 flex items-center gap-2 text-blue-600 hover:text-blue-700">
        <ArrowLeft size={20} /> Back to Tickets
      </button>

      <div className="rounded-lg bg-white p-8 shadow-lg dark:bg-slate-900">
        <h1 className="mb-2 text-3xl font-bold">{submission.ticket_title}</h1>
        <p className="mb-6 text-slate-600 dark:text-slate-300">Submission Feedback</p>

        <div className="mb-6 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-5xl font-bold">{submission.ai_score}/10</div>
              <div className="mt-2 text-blue-100">AI Grade ({submission.status})</div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold">+{submission.xp_granted ? submission.xp_awarded : 0} XP</div>
              {submission.duration_minutes != null && <div className="text-blue-100 text-sm mt-1">Time spent: {submission.duration_minutes} min</div>}
            </div>
          </div>
        </div>

        {!submission.xp_granted && (
          <div className="mb-6 rounded border border-amber-300 bg-amber-50 p-4 text-amber-800">
            Awaiting instructor verification. XP and mastery update after proof is verified.
          </div>
        )}

        {submission.duration_minutes != null && (
          <div className="mb-6 rounded bg-slate-50 p-4 dark:bg-slate-800/60">
            <div className="flex justify-between"><span>Time Spent</span><span className="font-semibold">{submission.duration_minutes} minutes</span></div>
            <div className="flex justify-between"><span>Average Time</span><span>{submission.avg_duration} minutes</span></div>
          </div>
        )}

        <div className="mb-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded border border-slate-200 p-4 dark:border-slate-700">
            <h2 className="mb-2 text-lg font-bold">Your Submission</h2>
            <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">{submission.writeup}</p>
            {submission.commands_used ? (
              <div className="mt-3 rounded bg-slate-100 p-2 dark:bg-slate-800">
                <p className="text-xs font-semibold uppercase text-slate-500">Commands Used</p>
                <pre className="whitespace-pre-wrap text-xs">{submission.commands_used}</pre>
              </div>
            ) : null}
          </div>
          <div className="rounded border border-slate-200 p-4 dark:border-slate-700">
            <h2 className="mb-2 text-lg font-bold">Admin / AI Feedback</h2>
            {feedback.feedback ? <p className="whitespace-pre-wrap text-sm">{feedback.feedback}</p> : <p className="text-sm text-slate-500">No feedback text.</p>}
          </div>
        </div>

        {feedback.strengths?.length > 0 && (
          <div className="mb-6">
            <div className="mb-3 flex items-center gap-2">
              <CheckCircle className="text-green-600" size={24} />
              <h2 className="text-xl font-bold text-green-900">Strengths</h2>
            </div>
            <ul className="space-y-2">
              {feedback.strengths.map((strength, i) => (
                <li key={i} className="flex items-start gap-2 rounded bg-green-50 p-3">
                  <span className="mt-1 text-green-600">+</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {feedback.weaknesses?.length > 0 && (
          <div className="mb-6">
            <div className="mb-3 flex items-center gap-2">
              <AlertCircle className="text-orange-600" size={24} />
              <h2 className="text-xl font-bold text-orange-900">Areas to Improve</h2>
            </div>
            <ul className="space-y-2">
              {feedback.weaknesses.map((weakness, i) => (
                <li key={i} className="flex items-start gap-2 rounded bg-orange-50 p-3">
                  <span className="mt-1 text-orange-600">!</span>
                  <span>{weakness}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {feedback.feedback && (
          <div className="mb-6">
            <div className="mb-3 flex items-center gap-2">
              <MessageSquare className="text-blue-600" size={24} />
              <h2 className="text-xl font-bold text-blue-900">Detailed Feedback</h2>
            </div>
            <div className="rounded bg-blue-50 p-4">
              <p className="whitespace-pre-wrap text-slate-800">{feedback.feedback}</p>
            </div>
          </div>
        )}

        {submission.admin_comment && (
          <div className="mb-6">
            <h2 className="mb-2 text-xl font-bold">Instructor Review</h2>
            <div className="rounded bg-slate-100 p-4 dark:bg-slate-800">{submission.admin_comment}</div>
          </div>
        )}

        {images.length > 0 && (
          <div className="mb-6">
            <h2 className="mb-3 text-xl font-bold">Screenshots</h2>
            <div className="flex flex-wrap gap-2">
              {images.map((src, i) => (
                <img key={src} src={src} className="h-24 w-24 cursor-pointer rounded object-cover" onClick={() => setLightboxIndex(i)} />
              ))}
            </div>
            <Lightbox open={lightboxIndex >= 0} close={() => setLightboxIndex(-1)} index={lightboxIndex >= 0 ? lightboxIndex : 0} slides={images.map((src) => ({ src }))} />
          </div>
        )}

        {submission.status === "needs_revision" ? (
          <button onClick={() => navigate(`/tickets/${submission.ticket_id}`)} className="mb-3 w-full rounded-lg bg-amber-600 py-3 font-semibold text-white hover:bg-amber-700">Resubmit</button>
        ) : null}
        <button onClick={() => navigate("/tickets")} className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-700">Back to Tickets</button>
      </div>
    </main>
  );
}
