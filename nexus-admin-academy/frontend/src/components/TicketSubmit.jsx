import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { submitTicket } from "../services/api";

export default function TicketSubmit({ ticket, studentId }) {
  const [writeup, setWriteup] = useState("");
  const [result, setResult] = useState(null);

  const onSubmit = async () => {
    const res = await submitTicket(ticket.id, { student_id: studentId, writeup });
    setResult(res.data);
  };

  return (
    <section className="panel space-y-3">
      <h2 className="text-xl font-semibold">{ticket.title}</h2>
      <p>{ticket.description}</p>
      <textarea
        className="h-40 w-full rounded border p-2"
        value={writeup}
        onChange={(e) => setWriteup(e.target.value)}
        placeholder="Write your troubleshooting steps..."
      />
      <button className="rounded bg-sky-600 px-4 py-2 text-white" onClick={onSubmit}>
        Submit Solution
      </button>

      <div className="rounded border p-3">
        <p className="mb-2 text-sm font-semibold">Markdown Preview</p>
        <ReactMarkdown>{writeup}</ReactMarkdown>
      </div>

      {result && (
        <div className="rounded border border-green-200 bg-green-50 p-3">
          <p>AI Score: {result.ai_score}/10</p>
          <p>XP Awarded: {result.xp_awarded}</p>
          <p>Feedback: {result.feedback.feedback}</p>
        </div>
      )}
    </section>
  );
}
