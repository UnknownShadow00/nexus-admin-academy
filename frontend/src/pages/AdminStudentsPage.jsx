import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { createStudent, deleteStudent, getStudentsOverview, updateStudent } from "../services/api";
import StudentTrainingDetail from "../components/StudentTrainingDetail";
import toast from "react-hot-toast";

export default function AdminStudentsPage() {
  const scrollContainerRef = useRef(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editUsername, setEditUsername] = useState("");
  const [editPassword, setEditPassword] = useState("");
  const [editIsMentor, setEditIsMentor] = useState(false);
  const [createError, setCreateError] = useState("");
  const [expandedStudentId, setExpandedStudentId] = useState(null);
  const [trainingProgressByStudent, setTrainingProgressByStudent] = useState({});

  const load = async () => {
    setLoading(true);
    const res = await getStudentsOverview();
    setRows(res.data || []);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const cacheStudentProgress = useCallback((studentId, progress) => {
    setTrainingProgressByStudent((current) => (
      current[studentId] ? current : { ...current, [studentId]: progress }
    ));
  }, []);

  const onCreate = async () => {
    try {
      setCreateError("");
      await createStudent({ name: newName, email: newEmail, username: newUsername, password: newPassword });
      toast.success("Student created");
      setNewName("");
      setNewEmail("");
      setNewUsername("");
      setNewPassword("");
      setCreating(false);
      await load();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to create student";
      setCreateError(msg);
    }
  };

  const onStartEdit = (row) => {
    setEditingId(row.student_id);
    setEditName(row.name || "");
    setEditEmail(row.email || "");
    setEditNotes(row.admin_notes || "");
    setEditUsername(row.username || "");
    setEditPassword("");
    setEditIsMentor(Boolean(row.is_mentor));
  };

  const onSaveEdit = async (studentId) => {
    try {
      const updates = { name: editName, email: editEmail, admin_notes: editNotes, username: editUsername, is_mentor: editIsMentor };
      if (editPassword.trim()) updates.password = editPassword;
      await updateStudent(studentId, updates);
      toast.success("Student updated");
      setEditingId(null);
      await load();
    } catch {
      toast.error("Failed to update student");
    }
  };

  const onDelete = async (studentId) => {
    if (!window.confirm("Delete this student? This cannot be undone.")) return;
    try {
      await deleteStudent(studentId);
      toast.success("Student deleted");
      await load();
    } catch {
      toast.error("Failed to delete student");
    }
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
        <div className="panel mb-4 grid gap-2 md:grid-cols-5 dark:bg-slate-900 dark:border-slate-700">
          <input className="input-field" placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <input className="input-field" placeholder="Email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
          <input className="input-field" placeholder="Username" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} />
          <input className="input-field" type="password" placeholder="Password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          <button
            className="btn-primary"
            onClick={onCreate}
            disabled={!newName.trim() || !newEmail.trim() || !newUsername.trim() || !newPassword.trim()}
          >
            Save
          </button>
          {createError ? <p className="col-span-5 text-sm text-red-600 dark:text-red-400">{createError}</p> : null}
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
      <div ref={scrollContainerRef} className="panel overflow-x-auto dark:bg-slate-900 dark:border-slate-700">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-2 py-2">#</th>
              <th className="px-2 py-2">Name</th>
              <th className="px-2 py-2">Email</th>
              <th className="px-2 py-2">Username</th>
              <th className="px-2 py-2">Notes</th>
              <th className="px-2 py-2">Mentor</th>
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
              const expanded = expandedStudentId === r.student_id;
              return (
                <Fragment key={r.student_id}>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <td className="px-2 py-2">{r.rank}</td>
                  <td className="px-2 py-2">
                    {editing ? <input className="input-field" value={editName} onChange={(e) => setEditName(e.target.value)} /> : r.name}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? <input className="input-field" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} /> : r.email}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? (
                      <input className="input-field" value={editUsername} onChange={(e) => setEditUsername(e.target.value)} />
                    ) : (
                      r.username || "-"
                    )}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? (
                      <input className="input-field" value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
                    ) : (
                      r.admin_notes || "-"
                    )}
                  </td>
                  <td className="px-2 py-2">
                    {editing ? (
                      <label className="flex cursor-pointer items-center gap-1 text-sm">
                        <input
                          type="checkbox"
                          checked={editIsMentor}
                          onChange={(e) => setEditIsMentor(e.target.checked)}
                          className="h-4 w-4"
                        />
                        Mentor
                      </label>
                    ) : (
                      r.is_mentor ? <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">Mentor</span> : null
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
                        <button
                          className="btn-secondary"
                          onClick={() => {
                            // The table scrolls horizontally on narrow viewports; this
                            // button lives in the last column, so reset scroll on expand
                            // or the detail content renders off-screen to the left.
                            if (!expanded) scrollContainerRef.current?.scrollTo({ left: 0 });
                            setExpandedStudentId(expanded ? null : r.student_id);
                          }}
                          aria-expanded={expanded}
                        >
                          {expanded ? "Hide details" : "Details"}
                        </button>
                        <button className="btn-secondary" onClick={() => onStartEdit(r)}>Edit</button>
                        <button className="btn-secondary" onClick={() => onDelete(r.student_id)}>Delete</button>
                      </div>
                    )}
                  </td>
                </tr>
                {expanded ? (
                  <tr className="border-b border-slate-200 bg-slate-50/70 dark:border-slate-700 dark:bg-slate-950/40">
                    <td className="px-4 py-4" colSpan={12}>
                      {/* Bounded width for readability; the "Details" click above resets
                          scrollContainerRef to the left so this is visible without the
                          admin needing to scroll back manually. */}
                      <div className="w-[92vw] max-w-3xl">
                        <StudentTrainingDetail
                          studentId={r.student_id}
                          cachedProgress={trainingProgressByStudent[r.student_id]}
                          onProgressLoaded={cacheStudentProgress}
                        />
                      </div>
                    </td>
                  </tr>
                ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      ) : null}
    </main>
  );
}
