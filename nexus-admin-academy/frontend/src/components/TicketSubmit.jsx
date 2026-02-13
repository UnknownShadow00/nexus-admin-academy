import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Spinner } from "./icons";
import { submitTicket } from "../services/api";

export default function TicketSubmit({ ticket, studentId }) {
  const [writeup, setWriteup] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setLoading(true);
    const res = await submitTicket(ticket.id, { student_id: studentId, writeup });
    setResult(res.data);
    setLoading(false);
  };

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <article className="panel space-y-3">
        <h2 className="text-2xl font-bold text-gray-900">{ticket.title}</h2>
        <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
          <p>{ticket.description}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Technical notes</p>
          <p className="mt-2 font-mono text-sm text-slate-700">Include command output, validation steps, and rollback notes where applicable.</p>
        </div>
      </article>

      <article className="panel space-y-3">
        <h3 className="text-xl font-semibold text-gray-900">Submit your solution</h3>
        <textarea
          className="input-field h-40 resize-none"
          value={writeup}
          onChange={(e) => setWriteup(e.target.value)}
          placeholder="Write your troubleshooting steps in markdown..."
        />

        <button className="btn-primary w-full" onClick={onSubmit} disabled={loading || !writeup.trim()}>
          {loading ? <span className="inline-flex items-center gap-2"><Spinner className="h-4 w-4 animate-spin" /> Grading...</span> : "Submit Solution"}
        </button>

        <div className="rounded-lg border border-slate-200 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Markdown Preview</p>
          <div className="prose prose-sm max-w-none text-slate-700">
            <ReactMarkdown>{writeup || "_Your preview will appear here._"}</ReactMarkdown>
          </div>
        </div>
      </article>

      {result && (
        <aside className="panel lg:col-span-2">
          <p className="text-lg font-bold text-emerald-700">AI Score: {result.ai_score}/10 · XP Awarded: {result.xp_awarded}</p>
          <p className="mt-1 text-sm text-slate-700">{result.feedback.feedback}</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div>
              <p className="font-semibold text-gray-900">Strengths</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">
                {result.feedback.strengths?.map((item, idx) => <li key={idx}>{item}</li>)}
              </ul>
            </div>
            <div>
              <p className="font-semibold text-gray-900">Weaknesses</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">
                {result.feedback.weaknesses?.map((item, idx) => <li key={idx}>{item}</li>)}
              </ul>
            </div>
          </div>
        </aside>
      )}
    </section>
  );
}
