import { useEffect, useState } from "react";
import {
  deleteAdminServiceDeskAssignment, getAdminServiceDeskAssignments, getAdminServiceDeskAttempts,
  getAdminServiceDeskBetaEnrollments, getAdminServiceDeskEvents, getAdminServiceDeskHealth,
  getAdminServiceDeskKnowledge, getAdminServiceDeskScenarios, removeAdminServiceDeskBetaEnrollment,
  resetAdminServiceDeskAttempt, saveAdminServiceDeskAssignment, saveAdminServiceDeskBetaEnrollment,
  saveAdminServiceDeskKnowledge,
} from "../../services/api";

export default function AdminServiceDeskPage() {
  const [scenarios, setScenarios] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [health, setHealth] = useState(null);
  const [replay, setReplay] = useState(null);
  const [error, setError] = useState("");
  const [studentId, setStudentId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [betaStudentId, setBetaStudentId] = useState("");
  const [knowledgeDraft, setKnowledgeDraft] = useState({ stable_id: "", title: "", category: "", content: "", status: "draft", skill_tags: [] });

  const load = async () => {
    try {
      setError("");
      const [s, a, g, h, b, k] = await Promise.all([
        getAdminServiceDeskScenarios({ suppressToast: true }), getAdminServiceDeskAttempts({ suppressToast: true }),
        getAdminServiceDeskAssignments({ suppressToast: true }), getAdminServiceDeskHealth({ suppressToast: true }),
        getAdminServiceDeskBetaEnrollments({ suppressToast: true }), getAdminServiceDeskKnowledge({ suppressToast: true }),
      ]);
      setScenarios(s.data); setAttempts(a.data); setAssignments(g.data); setHealth(h.data); setEnrollments(b.data); setKnowledge(k.data);
    } catch (err) { setError(err.userMessage || "Service Desk Lab administration is unavailable."); }
  };

  useEffect(() => { load(); }, []);
  const inspect = async (id) => setReplay((await getAdminServiceDeskEvents(id, { suppressToast: true })).data);
  const reset = async (id) => { await resetAdminServiceDeskAttempt(id); await load(); await inspect(id); };
  const assign = async (event) => { event.preventDefault(); await saveAdminServiceDeskAssignment({ student_id: Number(studentId), scenario_id: Number(scenarioId), mode: "learning", is_required: true }); setStudentId(""); setScenarioId(""); await load(); };
  const enroll = async (event) => { event.preventDefault(); await saveAdminServiceDeskBetaEnrollment({ student_id: Number(betaStudentId) }); setBetaStudentId(""); await load(); };
  const saveKnowledge = async (event) => { event.preventDefault(); await saveAdminServiceDeskKnowledge({ ...knowledgeDraft, skill_tags: knowledgeDraft.skill_tags.filter(Boolean) }); setKnowledgeDraft({ stable_id: "", title: "", category: "", content: "", status: "draft", skill_tags: [] }); await load(); };

  if (error) return <main className="mx-auto max-w-5xl p-6"><h1 className="text-2xl font-bold">Service Desk Lab</h1><p className="mt-3">{error}</p></main>;
  return <main className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
    <header><p className="text-sm font-semibold text-blue-600">ASSESSMENTS & LABS</p><h1 className="text-3xl font-bold">Service Desk Lab</h1><p className="text-slate-600 dark:text-slate-300">Private-beta scenario review, assignments, and deterministic event replay.</p></header>
    <section className="grid gap-3 md:grid-cols-3"><div className="panel"><p>Published scenarios</p><p className="text-3xl font-bold">{health?.published_count ?? "—"}</p></div><div className="panel"><p>Health</p><p className="text-3xl font-bold">{health?.valid ? "Passing" : "Pending"}</p></div><div className="panel"><p>Assignments</p><p className="text-3xl font-bold">{assignments.length}</p></div></section>
    <section className="grid gap-4 lg:grid-cols-2">
      <div className="panel"><h2 className="text-xl font-bold">Private beta enrollment</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Enrollment alone never enables student access; the student feature flag must also be on.</p><form className="mt-3 flex flex-wrap gap-2" onSubmit={enroll}><label className="sr-only" htmlFor="beta-student-id">Student ID</label><input id="beta-student-id" className="input-field max-w-40" required min="1" type="number" value={betaStudentId} onChange={(event) => setBetaStudentId(event.target.value)} placeholder="Student ID" /><button className="btn-primary" type="submit">Add beta student</button></form><ul className="mt-4 space-y-2 text-sm">{enrollments.map((item) => <li className="flex flex-wrap items-center justify-between gap-2 rounded border p-2" key={item.id}><span>Student {item.student_id} · {item.enabled && !item.removed_at ? "Active" : "Removed"}</span>{item.enabled && !item.removed_at ? <button className="btn-secondary" type="button" onClick={async () => { await removeAdminServiceDeskBetaEnrollment(item.student_id); await load(); }}>Remove</button> : null}</li>)}</ul></div>
      <div className="panel"><h2 className="text-xl font-bold">Assign scenario</h2><form className="mt-3 flex flex-wrap gap-2" onSubmit={assign}><label className="sr-only" htmlFor="student-id">Student ID</label><input id="student-id" className="input-field max-w-40" required min="1" type="number" value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="Student ID" /><label className="sr-only" htmlFor="scenario-id">Scenario ID</label><select id="scenario-id" className="input-field max-w-64" required value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}><option value="">Choose scenario</option>{scenarios.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><button className="btn-primary" type="submit">Assign learning mode</button></form><ul className="mt-4 space-y-2 text-sm">{assignments.map((item) => <li className="flex flex-wrap items-center justify-between gap-2 rounded border p-2" key={item.id}><span>Student {item.student_id} · Scenario {item.scenario_id} · {item.mode}</span><button className="btn-secondary" type="button" onClick={async () => { await deleteAdminServiceDeskAssignment(item.id); await load(); }}>Remove</button></li>)}</ul></div>
    </section>
    <section className="panel"><h2 className="text-xl font-bold">Scenarios and validation</h2><ul className="mt-3 grid gap-2 md:grid-cols-2">{scenarios.map((item) => <li key={item.id} className="rounded border p-3"><strong>{item.title}</strong><br /><span className="text-sm">{item.stable_key} · {item.status}</span></li>)}</ul></section>
    <section className="panel"><h2 className="text-xl font-bold">Knowledge Base</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Published articles are student-visible; drafts remain administrator-only.</p><form className="mt-3 grid gap-2 md:grid-cols-2" onSubmit={saveKnowledge}><input aria-label="Knowledge article stable ID" className="input-field" required value={knowledgeDraft.stable_id} onChange={(event) => setKnowledgeDraft({ ...knowledgeDraft, stable_id: event.target.value })} placeholder="Stable ID" /><input aria-label="Knowledge article title" className="input-field" required value={knowledgeDraft.title} onChange={(event) => setKnowledgeDraft({ ...knowledgeDraft, title: event.target.value })} placeholder="Title" /><input aria-label="Knowledge article category" className="input-field" required value={knowledgeDraft.category} onChange={(event) => setKnowledgeDraft({ ...knowledgeDraft, category: event.target.value })} placeholder="Category" /><select aria-label="Knowledge article status" className="input-field" value={knowledgeDraft.status} onChange={(event) => setKnowledgeDraft({ ...knowledgeDraft, status: event.target.value })}><option value="draft">Draft</option><option value="published">Published</option></select><textarea aria-label="Knowledge article content" className="input-field min-h-24 md:col-span-2" required value={knowledgeDraft.content} onChange={(event) => setKnowledgeDraft({ ...knowledgeDraft, content: event.target.value })} placeholder="Article content" /><button className="btn-primary w-fit" type="submit">Save article</button></form><ul className="mt-4 grid gap-2 md:grid-cols-2">{knowledge.map((article) => <li className="rounded border p-3" key={article.id}><strong>{article.title}</strong><p className="text-sm">{article.category} · {article.status}</p></li>)}</ul></section>
    <section className="panel overflow-x-auto"><h2 className="text-xl font-bold">Attempts</h2><table className="mt-3 w-full min-w-[620px] text-left text-sm"><thead><tr><th>ID</th><th>Student</th><th>Version</th><th>Mode</th><th>Result</th><th>Actions</th></tr></thead><tbody>{attempts.map((item) => <tr className="border-t" key={item.id}><td className="py-2">{item.id}</td><td>{item.student_id}</td><td>{item.scenario_version_id}</td><td>{item.mode}</td><td>{item.status} · {item.score ?? 0}%</td><td><button className="btn-secondary mr-2" type="button" onClick={() => inspect(item.id)}>Replay</button>{item.mode === "simulation" && item.status !== "in_progress" ? <button className="btn-secondary" type="button" onClick={() => reset(item.id)}>Reset</button> : null}</td></tr>)}</tbody></table></section>
    {replay ? <section className="panel"><h2 className="text-xl font-bold">Attempt {replay.attempt.id} event replay</h2><p className="mt-2">Score: {replay.grade?.overall_score ?? 0}% · {replay.grade?.passed ? "Passed" : "Not passed"}</p><ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">{replay.events.map((event) => <li key={event.sequence_number}><strong>{event.tool}</strong> · {event.event_type} · {event.success ? "accepted" : "rejected"}</li>)}</ol></section> : null}
  </main>;
}
