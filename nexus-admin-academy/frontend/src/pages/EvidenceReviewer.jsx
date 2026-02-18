import { useEffect, useState } from "react";
import { getEvidence, reviewEvidence } from "../services/api";

export default function EvidenceReviewer() {
  const [status, setStatus] = useState("pending");
  const [rows, setRows] = useState([]);
  const [note, setNote] = useState("");

  const load = async () => {
    const res = await getEvidence(status || undefined);
    setRows(res.data || []);
  };

  useEffect(() => {
    load();
  }, [status]);

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold">Evidence Reviewer</h1>
        <div className="mt-3 flex gap-2">
          <select className="input-field max-w-60" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="valid">Valid</option>
            <option value="suspicious">Suspicious</option>
            <option value="rejected">Rejected</option>
          </select>
          <input className="input-field flex-1" placeholder="Review note" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      </section>
      <section className="space-y-2">
        {rows.map((row) => (
          <article key={row.id} className="panel flex flex-wrap items-center justify-between gap-2 dark:border-slate-700 dark:bg-slate-900">
            <div>
              <p className="font-medium">#{row.id} - {row.artifact_type} - {row.validation_status}</p>
              <p className="text-xs text-slate-500">{row.storage_key}</p>
            </div>
            <div className="flex gap-2">
              <button className="btn-secondary" onClick={async () => { await reviewEvidence(row.id, { validation_status: "valid", validation_notes: note }); await load(); }}>Mark Valid</button>
              <button className="btn-secondary" onClick={async () => { await reviewEvidence(row.id, { validation_status: "suspicious", validation_notes: note }); await load(); }}>Suspicious</button>
              <button className="btn-secondary" onClick={async () => { await reviewEvidence(row.id, { validation_status: "rejected", validation_notes: note }); await load(); }}>Reject</button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

