import { useEffect, useState } from "react";
import { createStudent, deleteStudent, getStudentsOverview, updateStudent } from "../services/api";

export default function AdminStudentsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editNotes, setEditNotes] = useState("");

  const load = async () => {
    setLoading(true);
    const res = await getStudentsOverview();
    setRows(res.data || []);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async () => {
    await createStudent({ name: newName, email: newEmail });
    setNewName("");
    setNewEmail("");
    setCreating(false);
    await load();
  };

  const onStartEdit = (row) => {
    setEditingId(row.student_id);
    setEditName(row.name || "");
    setEditEmail(row.email || "");
    setEditNotes(row.admin_notes || "");
  };

  const onSaveEdit = async (studentId) => {
    await updateStudent(studentId, { name: editName, email: editEmail, admin_notes: editNotes });
    setEditingId(null);
    await load();
  };

  const onDelete = async (studentId) => {
    if (!window.confirm("Delete this student? This cannot be undone.")) return;
    await deleteStudent(studentId);
    await load();
  };

  return (
    <main className="mx-auto max-w-7xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Student Activity Overview</h1>
        <button className="btn-primary" onClick={() => setCreating((v) => !v)}>
          {creating ? "Cancel" : "New Student"}
        </button>
      </div>

      {creating ? (
        <div className="panel mb-4 grid gap-2 md:grid-cols-3 dark:bg-slate-900 dark:border-slate-700">
          <input className="input-field" placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <input className="input-field" placeholder="Email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
          <button className="btn-primary" onClick={onCreate} disabled={!newName.trim() || !newEmail.trim()}>
            Save
          </button>
        </div>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((id) => (
            <div key={id} className="panel animate-pulse dark:border-slate-700 dark:bg-slate-900">
              <div className="h-5 w-2/3 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="mt-3 h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-2 h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-4 h-9 w-full rounded bg-slate-200 dark:bg-slate-700" />
            </div>
          ))}
        </div>
      ) : null}

      {!loading ? (
      <div className="panel overflow-x-auto dark:bg-slate-900 dark:border-slate-700">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-2 py-2">#</th>
              <th className="px-2 py-2">Name</th>
              <th className="px-2 py-2">Email</th>
              <th className="px-2 py-2">Notes</th>
              <th className="px-2 py-2">XP</th>
              <th className="px-2 py-2">Quiz</th>
              <th className="px-2 py-2">Avg Quiz</th>
              <th className="px-2 py-2">Tickets</th>
              <th className="px-2 py-2">Avg Ticket</th>
              <th className="px-2 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const editing = editingId === r.student_id;
              return (
                <tr key={r.student_id} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="px-2 py-2">{r.rank}</td>
                  <td className="px-2 py-2">
                    {editing ? <input className="input-field" value={editName} onChange={(e) => setEditName(e.target.value)} /> : r.name}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? <input className="input-field" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} /> : r.email}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? (
                      <input className="input-field" value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
                    ) : (
                      r.admin_notes || "-"
                    )}
                  </td>
                  <td className="px-2 py-2">{r.xp}</td>
                  <td className="px-2 py-2">{r.quiz_done}/{r.quiz_total}</td>
                  <td className="px-2 py-2">{r.avg_quiz}</td>
                  <td className="px-2 py-2">{r.ticket_done}/{r.ticket_total}</td>
                  <td className="px-2 py-2">{r.avg_ticket}</td>
                  <td className="px-2 py-2">
                    {editing ? (
                      <div className="flex gap-2">
                        <button className="btn-primary" onClick={() => onSaveEdit(r.student_id)}>Save</button>
                        <button className="btn-secondary" onClick={() => setEditingId(null)}>Cancel</button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button className="btn-secondary" onClick={() => onStartEdit(r)}>Edit</button>
                        <button className="btn-secondary" onClick={() => onDelete(r.student_id)}>Delete</button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      ) : null}
    </main>
  );
}
