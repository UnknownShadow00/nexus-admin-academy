import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import EmptyState from "./EmptyState";
import { bulkGenerateTickets, bulkPublishTickets, createResource, createTicket, generateQuiz, getSubmissions } from "../services/api";

export default function AdminDashboard() {
  const [submissions, setSubmissions] = useState([]);
  const [quizForm, setQuizForm] = useState({ source_url: "", week_number: 1, title: "", domain_id: "1.0" });
  const [ticketForm, setTicketForm] = useState({ title: "", description: "", difficulty: 1, week_number: 1, domain_id: "1.0" });
  const [resourceForm, setResourceForm] = useState({ title: "", url: "", resource_type: "Video", week_number: 1, category: "" });
  const [bulkText, setBulkText] = useState("");
  const [bulkWeek, setBulkWeek] = useState(1);
  const [bulkDifficulty, setBulkDifficulty] = useState(2);
  const [generated, setGenerated] = useState([]);

  const load = async () => {
    const res = await getSubmissions();
    setSubmissions(res.data || []);
  };

  useEffect(() => {
    load();
  }, []);

  const avgScore = useMemo(() => {
    if (!submissions.length) return 0;
    const total = submissions.reduce((sum, item) => sum + (item.ai_score || 0), 0);
    return (total / submissions.length).toFixed(1);
  }, [submissions]);

  return (
    <div className="space-y-4">
      <section className="grid gap-3 md:grid-cols-3">
        <article className="panel dark:border-slate-700 dark:bg-slate-900"><p className="text-sm">Submissions</p><p className="text-2xl font-bold">{submissions.length}</p></article>
        <article className="panel dark:border-slate-700 dark:bg-slate-900"><p className="text-sm">Average score</p><p className="text-2xl font-bold">{avgScore}/10</p></article>
        <article className="panel dark:border-slate-700 dark:bg-slate-900"><p className="text-sm">Completion rate</p><p className="text-2xl font-bold">{Math.min(100, Math.round((new Set(submissions.map((x) => x.student_name)).size / 5) * 100))}%</p></article>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Generate Quiz</h2>
          <input className="input-field" placeholder="Source URL" value={quizForm.source_url} onChange={(e) => setQuizForm({ ...quizForm, source_url: e.target.value })} />
          <input className="input-field" placeholder="Title" value={quizForm.title} onChange={(e) => setQuizForm({ ...quizForm, title: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" value={quizForm.week_number} onChange={(e) => setQuizForm({ ...quizForm, week_number: Number(e.target.value || 1) })} />
            <select className="input-field" value={quizForm.domain_id} onChange={(e) => setQuizForm({ ...quizForm, domain_id: e.target.value })}>
              <option value="1.0">1.0 Hardware</option>
              <option value="2.0">2.0 Networking</option>
              <option value="3.0">3.0 Software Troubleshooting</option>
              <option value="4.0">4.0 Security / Procedures</option>
            </select>
          </div>
          <button className="btn-primary" onClick={async () => {
            const t = toast.loading("Generating quiz...");
            try {
              await generateQuiz(quizForm);
              toast.success("Quiz created successfully");
            } finally {
              toast.dismiss(t);
            }
          }}>
            Generate Quiz
          </button>
        </article>

        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Create Ticket</h2>
          <input className="input-field" placeholder="Title" value={ticketForm.title} onChange={(e) => setTicketForm({ ...ticketForm, title: e.target.value })} />
          <textarea className="input-field" placeholder="Description" value={ticketForm.description} onChange={(e) => setTicketForm({ ...ticketForm, description: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" value={ticketForm.difficulty} onChange={(e) => setTicketForm({ ...ticketForm, difficulty: Number(e.target.value || 1) })} />
            <input className="input-field" type="number" value={ticketForm.week_number} onChange={(e) => setTicketForm({ ...ticketForm, week_number: Number(e.target.value || 1) })} />
          </div>
          <select className="input-field" value={ticketForm.domain_id} onChange={(e) => setTicketForm({ ...ticketForm, domain_id: e.target.value })}>
            <option value="1.0">1.0 Hardware</option>
            <option value="2.0">2.0 Networking</option>
            <option value="3.0">3.0 Software Troubleshooting</option>
            <option value="4.0">4.0 Security / Procedures</option>
          </select>
          <button className="btn-primary" onClick={async () => { await createTicket(ticketForm); toast.success("Ticket created"); }}>
            Create Ticket
          </button>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Add Resource</h2>
          <input className="input-field" placeholder="Title" value={resourceForm.title} onChange={(e) => setResourceForm({ ...resourceForm, title: e.target.value })} />
          <input className="input-field" placeholder="URL" value={resourceForm.url} onChange={(e) => setResourceForm({ ...resourceForm, url: e.target.value })} />
          <div className="grid grid-cols-3 gap-2">
            <select className="input-field" value={resourceForm.resource_type} onChange={(e) => setResourceForm({ ...resourceForm, resource_type: e.target.value })}>
              <option>Video</option><option>Article</option><option>Study Guide</option><option>Other</option>
            </select>
            <input className="input-field" type="number" value={resourceForm.week_number} onChange={(e) => setResourceForm({ ...resourceForm, week_number: Number(e.target.value || 1) })} />
            <input className="input-field" placeholder="Category" value={resourceForm.category} onChange={(e) => setResourceForm({ ...resourceForm, category: e.target.value })} />
          </div>
          <button className="btn-primary" onClick={async () => { await createResource(resourceForm); toast.success("Resource created"); }}>
            Save Resource
          </button>
        </article>

        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Bulk Create Tickets</h2>
          <textarea className="input-field h-32" placeholder="One title per line" value={bulkText} onChange={(e) => setBulkText(e.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" value={bulkWeek} onChange={(e) => setBulkWeek(Number(e.target.value || 1))} />
            <input className="input-field" type="number" value={bulkDifficulty} onChange={(e) => setBulkDifficulty(Number(e.target.value || 2))} />
          </div>
          <button className="btn-secondary" onClick={async () => {
            const titles = bulkText.split("\n").map((x) => x.trim()).filter(Boolean);
            const res = await bulkGenerateTickets({ titles, week_number: bulkWeek, difficulty: bulkDifficulty });
            const generatedItems = Array.isArray(res.data) ? res.data : (res.data?.tickets || []);
            setGenerated(generatedItems);
            toast.success("Draft descriptions generated");
          }}>Generate Descriptions</button>
          <button className="btn-primary" onClick={async () => {
            const publishPayload = generated
              .filter((x) => x.success !== false && x.title && x.description)
              .map((x) => ({
                title: x.title,
                description: x.description,
                difficulty: x.difficulty ?? bulkDifficulty,
                week_number: x.week_number ?? bulkWeek,
                domain_id: x.domain_id ?? "1.0",
              }));

            if (!publishPayload.length) {
              toast.error("No valid generated tickets to publish");
              return;
            }

            await bulkPublishTickets(publishPayload);
            toast.success("Bulk tickets published");
          }} disabled={!generated.length}>Publish All Tickets</button>
        </article>
      </section>

      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-2 text-xl font-semibold">Submissions</h2>
        {!submissions.length ? <EmptyState icon="??" title="No submissions yet" message="Student work will appear here after they complete tickets" /> : (
          <div className="space-y-2">
            {submissions.map((s) => (
              <div key={s.id} className="rounded border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-sm">{s.student_name} - {s.ticket_title} - {s.ai_score ?? "pending"}/10</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
