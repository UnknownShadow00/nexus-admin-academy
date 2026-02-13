import { useEffect, useMemo, useState } from "react";
import { Award, BookOpen, Spinner, Ticket } from "./icons";
import { createTicket, generateQuiz, getSubmissions, overrideSubmission } from "../services/api";

export default function AdminDashboard() {
  const [submissions, setSubmissions] = useState([]);
  const [quizForm, setQuizForm] = useState({ source_url: "", week_number: 1, title: "" });
  const [ticketState, setTicketState] = useState({ title: "", description: "", difficulty: 1, week_number: 1 });
  const [overrideScore, setOverrideScore] = useState(10);
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const res = await getSubmissions();
    setSubmissions(res.data.submissions);
  };

  useEffect(() => {
    load();
  }, []);

  const avgScore = useMemo(() => {
    if (!submissions.length) return 0;
    return (submissions.reduce((sum, sub) => sum + sub.ai_score, 0) / submissions.length).toFixed(1);
  }, [submissions]);

  const completionRate = useMemo(() => {
    const uniqueStudents = new Set(submissions.map((sub) => sub.student_name));
    return ((uniqueStudents.size / 5) * 100).toFixed(0);
  }, [submissions]);

  const statCards = [
    { label: "Total submissions", value: submissions.length, Icon: Ticket, tone: "text-blue-600" },
    { label: "Average score", value: `${avgScore}/10`, Icon: Award, tone: "text-emerald-600" },
    { label: "Completion rate", value: `${completionRate}%`, Icon: BookOpen, tone: "text-amber-600" },
  ];

  return (
    <div className="space-y-4">
      {statusMessage && (
        <div className="fixed right-6 top-24 z-20 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg">
          {statusMessage}
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-3">
        {statCards.map(({ label, value, Icon, tone }) => (
          <article key={label} className="panel">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500">{label}</p>
              <Icon className={`h-4 w-4 ${tone}`} />
            </div>
            <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="panel space-y-3">
          <h2 className="text-xl font-bold text-gray-900">Create Quiz</h2>
          <input className="input-field" placeholder="Source URL" onChange={(e) => setQuizForm({ ...quizForm, source_url: e.target.value })} />
          <input className="input-field" placeholder="Quiz title" onChange={(e) => setQuizForm({ ...quizForm, title: e.target.value })} />
          <input className="input-field" type="number" value={quizForm.week_number} onChange={(e) => setQuizForm({ ...quizForm, week_number: Number(e.target.value) })} />
          <button
            className="btn-primary w-full"
            onClick={async () => {
              setLoading(true);
              await generateQuiz(quizForm);
              setStatusMessage("Quiz generated and saved.");
              setLoading(false);
            }}
            disabled={loading}
          >
            {loading ? <span className="inline-flex items-center gap-2"><Spinner className="h-4 w-4 animate-spin" /> Working...</span> : "Create Quiz"}
          </button>
        </article>

        <article className="panel space-y-3">
          <h2 className="text-xl font-bold text-gray-900">Create Ticket</h2>
          <input className="input-field" placeholder="Ticket title" onChange={(e) => setTicketState({ ...ticketState, title: e.target.value })} />
          <textarea className="input-field" placeholder="Description" onChange={(e) => setTicketState({ ...ticketState, description: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" value={ticketState.difficulty} onChange={(e) => setTicketState({ ...ticketState, difficulty: Number(e.target.value) })} />
            <input className="input-field" type="number" value={ticketState.week_number} onChange={(e) => setTicketState({ ...ticketState, week_number: Number(e.target.value) })} />
          </div>
          <button
            className="btn-primary w-full"
            onClick={async () => {
              setLoading(true);
              await createTicket(ticketState);
              setStatusMessage("Ticket created successfully.");
              setLoading(false);
            }}
            disabled={loading}
          >
            {loading ? <span className="inline-flex items-center gap-2"><Spinner className="h-4 w-4 animate-spin" /> Working...</span> : "Create Ticket"}
          </button>
        </article>
      </section>

      <section className="panel">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl font-bold text-gray-900">Submissions</h2>
          <div className="flex items-center gap-2">
            <select className="input-field w-36" defaultValue="all">
              <option value="all">All students</option>
            </select>
            <input type="number" className="input-field w-24" min={0} max={10} value={overrideScore} onChange={(e) => setOverrideScore(Number(e.target.value))} />
          </div>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="px-3 py-2 font-semibold">Student ↕</th>
                <th className="px-3 py-2 font-semibold">Ticket ↕</th>
                <th className="px-3 py-2 font-semibold">Score ↕</th>
                <th className="px-3 py-2 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((s, idx) => (
                <tr key={s.id} className={idx % 2 ? "bg-slate-50" : "bg-white"}>
                  <td className="px-3 py-2">{s.student_name}</td>
                  <td className="px-3 py-2">{s.ticket_title}</td>
                  <td className="px-3 py-2 font-semibold text-gray-900">{s.ai_score}/10</td>
                  <td className="px-3 py-2">
                    <button
                      className="btn-secondary"
                      onClick={async () => {
                        await overrideSubmission(s.id, { new_score: overrideScore });
                        await load();
                        setStatusMessage(`Submission ${s.id} overridden to ${overrideScore}.`);
                      }}
                    >
                      Override
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!submissions.length && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-500">No submissions yet.</p>}
      </section>
    </div>
  );
}
