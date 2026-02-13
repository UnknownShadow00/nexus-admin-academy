import { useEffect, useState } from "react";
import { createTicket, generateQuiz, getSubmissions, overrideSubmission } from "../services/api";

export default function AdminDashboard() {
  const [submissions, setSubmissions] = useState([]);
  const [quizForm, setQuizForm] = useState({ source_url: "", week_number: 1, title: "" });
  const [ticketState, setTicketState] = useState({ title: "", description: "", difficulty: 1, week_number: 1 });

  const load = async () => {
    const res = await getSubmissions();
    setSubmissions(res.data.submissions);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <section className="panel space-y-2">
        <h2 className="text-xl font-semibold">Generate Quiz</h2>
        <input className="w-full rounded border p-2" placeholder="Source URL" onChange={(e) => setQuizForm({ ...quizForm, source_url: e.target.value })} />
        <input className="w-full rounded border p-2" placeholder="Title" onChange={(e) => setQuizForm({ ...quizForm, title: e.target.value })} />
        <input className="w-full rounded border p-2" type="number" value={quizForm.week_number} onChange={(e) => setQuizForm({ ...quizForm, week_number: Number(e.target.value) })} />
        <button className="rounded bg-sky-600 px-4 py-2 text-white" onClick={() => generateQuiz(quizForm)}>
          Generate Quiz
        </button>
      </section>

      <section className="panel space-y-2">
        <h2 className="text-xl font-semibold">Create Ticket</h2>
        <input className="w-full rounded border p-2" placeholder="Title" onChange={(e) => setTicketState({ ...ticketState, title: e.target.value })} />
        <textarea className="w-full rounded border p-2" placeholder="Description" onChange={(e) => setTicketState({ ...ticketState, description: e.target.value })} />
        <input className="w-full rounded border p-2" type="number" value={ticketState.difficulty} onChange={(e) => setTicketState({ ...ticketState, difficulty: Number(e.target.value) })} />
        <input className="w-full rounded border p-2" type="number" value={ticketState.week_number} onChange={(e) => setTicketState({ ...ticketState, week_number: Number(e.target.value) })} />
        <button className="rounded bg-sky-600 px-4 py-2 text-white" onClick={() => createTicket(ticketState)}>
          Create Ticket
        </button>
      </section>

      <section className="panel">
        <h2 className="text-xl font-semibold">Submissions</h2>
        <div className="mt-2 space-y-2">
          {submissions.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded border p-2">
              <span>
                {s.student_name} - {s.ticket_title} ({s.ai_score}/10)
              </span>
              <button className="rounded border px-3 py-1" onClick={async () => { await overrideSubmission(s.id, { new_score: 10 }); await load(); }}>
                Override to 10
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
