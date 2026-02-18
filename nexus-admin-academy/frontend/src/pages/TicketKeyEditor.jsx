import { useEffect, useMemo, useState } from "react";
import { getTickets, updateTicketAnswerKey } from "../services/api";

export default function TicketKeyEditor() {
  const [tickets, setTickets] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({
    root_cause: "",
    root_cause_type: "",
    required_checkpoints: '{ "checkpoints": [] }',
    required_evidence: '{ "evidence_types": [] }',
    scoring_anchors: "{}",
    model_answer: "",
  });

  useEffect(() => {
    const run = async () => {
      const res = await getTickets(undefined, undefined);
      setTickets(res.data || []);
    };
    run();
  }, []);

  const selected = useMemo(() => tickets.find((t) => t.id === selectedId), [tickets, selectedId]);

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-2">
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="mb-3 text-2xl font-bold">Ticket Answer Key Editor</h1>
        <div className="max-h-[70vh] space-y-2 overflow-auto">
          {tickets.map((ticket) => (
            <button key={ticket.id} className={`w-full rounded border p-3 text-left ${selectedId === ticket.id ? "border-blue-400 bg-blue-50 dark:bg-slate-800" : "border-slate-200 dark:border-slate-700"}`} onClick={() => setSelectedId(ticket.id)}>
              <p className="font-medium">{ticket.title}</p>
              <p className="text-xs text-slate-500">Difficulty {ticket.difficulty} - Week {ticket.week_number}</p>
            </button>
          ))}
        </div>
      </section>
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-3 text-xl font-bold">{selected ? selected.title : "Select a ticket"}</h2>
        {selected ? (
          <div className="space-y-2">
            <input className="input-field" placeholder="Root cause" value={form.root_cause} onChange={(e) => setForm({ ...form, root_cause: e.target.value })} />
            <input className="input-field" placeholder="Root cause type" value={form.root_cause_type} onChange={(e) => setForm({ ...form, root_cause_type: e.target.value })} />
            <textarea className="input-field h-24" placeholder="Required checkpoints JSON" value={form.required_checkpoints} onChange={(e) => setForm({ ...form, required_checkpoints: e.target.value })} />
            <textarea className="input-field h-24" placeholder="Required evidence JSON" value={form.required_evidence} onChange={(e) => setForm({ ...form, required_evidence: e.target.value })} />
            <textarea className="input-field h-24" placeholder="Scoring anchors JSON" value={form.scoring_anchors} onChange={(e) => setForm({ ...form, scoring_anchors: e.target.value })} />
            <textarea className="input-field h-20" placeholder="Model answer" value={form.model_answer} onChange={(e) => setForm({ ...form, model_answer: e.target.value })} />
            <button
              className="btn-primary"
              onClick={async () => {
                await updateTicketAnswerKey(selected.id, {
                  root_cause: form.root_cause,
                  root_cause_type: form.root_cause_type,
                  required_checkpoints: JSON.parse(form.required_checkpoints || "{}"),
                  required_evidence: JSON.parse(form.required_evidence || "{}"),
                  scoring_anchors: JSON.parse(form.scoring_anchors || "{}"),
                  model_answer: form.model_answer,
                });
              }}
            >
              Save Answer Key
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}

