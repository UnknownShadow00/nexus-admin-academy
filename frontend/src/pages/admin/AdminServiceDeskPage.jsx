import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  deleteAdminServiceDeskAssignment,
  getAdminServiceDeskAssignments,
  getAdminServiceDeskAttempts,
  getAdminServiceDeskBetaEnrollments,
  getAdminServiceDeskEvents,
  getAdminServiceDeskHealth,
  getAdminServiceDeskKnowledge,
  getAdminServiceDeskScenarioDetails,
  getAdminServiceDeskScenarios,
  removeAdminServiceDeskBetaEnrollment,
  resetAdminServiceDeskAttempt,
  saveAdminServiceDeskAssignment,
  saveAdminServiceDeskBetaEnrollment,
  saveAdminServiceDeskKnowledge,
} from "../../services/api";

const emptyKnowledgeDraft = {
  stable_id: "",
  title: "",
  category: "",
  content: "",
  status: "draft",
  skill_tags: [],
};

function DefinitionList({ label, values }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-slate-600 dark:text-slate-300">{label}</dt>
      <dd className="mt-1">{values?.length ? values.join(", ") : "None"}</dd>
    </div>
  );
}

export default function AdminServiceDeskPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [scenarios, setScenarios] = useState([]);
  const [scenarioDetails, setScenarioDetails] = useState(null);
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
  const [newArticle, setNewArticle] = useState(emptyKnowledgeDraft);
  const [articleDraft, setArticleDraft] = useState(emptyKnowledgeDraft);

  const selectedScenarioKey = searchParams.get("scenario");
  const selectedArticleKey = searchParams.get("article");
  const selectedAttemptId = searchParams.get("attempt");
  const attemptPanel = searchParams.get("panel") || "replay";
  const editingArticle = searchParams.get("edit") === "1";
  const selectedArticle = knowledge.find((article) => article.stable_id === selectedArticleKey);

  const load = async () => {
    try {
      setError("");
      const [scenarioResponse, attemptResponse, assignmentResponse, healthResponse, enrollmentResponse, knowledgeResponse] = await Promise.all([
        getAdminServiceDeskScenarios({ suppressToast: true }),
        getAdminServiceDeskAttempts({ suppressToast: true }),
        getAdminServiceDeskAssignments({ suppressToast: true }),
        getAdminServiceDeskHealth({ suppressToast: true }),
        getAdminServiceDeskBetaEnrollments({ suppressToast: true }),
        getAdminServiceDeskKnowledge({ suppressToast: true }),
      ]);
      setScenarios(scenarioResponse.data);
      setAttempts(attemptResponse.data);
      setAssignments(assignmentResponse.data);
      setHealth(healthResponse.data);
      setEnrollments(enrollmentResponse.data);
      setKnowledge(knowledgeResponse.data);
    } catch (err) {
      setError(err.userMessage || "Service Desk Lab administration is unavailable.");
    }
  };

  useEffect(() => { void load(); }, []);

  useEffect(() => {
    if (!selectedScenarioKey) {
      setScenarioDetails(null);
      return;
    }
    const scenario = scenarios.find((item) => item.stable_key === selectedScenarioKey);
    if (!scenario) return;
    getAdminServiceDeskScenarioDetails(scenario.id, { suppressToast: true })
      .then((response) => setScenarioDetails(response.data))
      .catch((err) => setError(err.userMessage || "Scenario details could not be loaded."));
  }, [scenarios, selectedScenarioKey]);

  useEffect(() => {
    if (selectedArticle) setArticleDraft({ ...selectedArticle });
  }, [selectedArticleKey, selectedArticle]);

  useEffect(() => {
    if (!selectedAttemptId) {
      setReplay(null);
      return;
    }
    getAdminServiceDeskEvents(selectedAttemptId, { suppressToast: true })
      .then((response) => setReplay(response.data))
      .catch((err) => setError(err.userMessage || "Attempt details could not be loaded."));
  }, [selectedAttemptId]);

  const showScenario = (stableKey) => setSearchParams({ scenario: stableKey });
  const showArticle = (stableId) => setSearchParams({ article: stableId });
  const showAttempt = (attemptId, panel) => setSearchParams({ attempt: String(attemptId), panel });
  const clearDetails = () => setSearchParams({});

  const assign = async (event) => {
    event.preventDefault();
    await saveAdminServiceDeskAssignment({
      student_id: Number(studentId),
      scenario_id: Number(scenarioId),
      mode: "learning",
      is_required: true,
    });
    setStudentId("");
    setScenarioId("");
    await load();
  };

  const enroll = async (event) => {
    event.preventDefault();
    await saveAdminServiceDeskBetaEnrollment({ student_id: Number(betaStudentId) });
    setBetaStudentId("");
    await load();
  };

  const createKnowledge = async (event) => {
    event.preventDefault();
    const response = await saveAdminServiceDeskKnowledge({
      ...newArticle,
      skill_tags: newArticle.skill_tags.filter(Boolean),
    });
    setNewArticle(emptyKnowledgeDraft);
    await load();
    showArticle(response.data.stable_id);
  };

  const updateKnowledge = async (event) => {
    event.preventDefault();
    await saveAdminServiceDeskKnowledge({
      stable_id: articleDraft.stable_id,
      title: articleDraft.title,
      category: articleDraft.category,
      content: articleDraft.content,
      status: articleDraft.status,
      skill_tags: articleDraft.skill_tags.filter(Boolean),
    });
    await load();
    setSearchParams({ article: articleDraft.stable_id }, { replace: true });
  };

  const reset = async (id) => {
    const response = await resetAdminServiceDeskAttempt(id);
    setReplay(response.data);
    await load();
  };

  if (error && !scenarios.length) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="text-2xl font-bold">Service Desk Lab</h1>
        <p className="mt-3" role="alert">{error}</p>
      </main>
    );
  }

  if (selectedScenarioKey && scenarioDetails) {
    return (
      <main className="mx-auto max-w-5xl space-y-5 p-4 md:p-6">
        <button className="btn-secondary" type="button" onClick={clearDetails}>Back to scenarios</button>
        <header>
          <p className="text-sm font-semibold text-blue-600">SCENARIO DETAILS</p>
          <h1 className="text-3xl font-bold">{scenarioDetails.name}</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-300">{scenarioDetails.description}</p>
        </header>
        <section className="panel" aria-labelledby="scenario-summary-heading">
          <h2 id="scenario-summary-heading" className="text-xl font-bold">Scenario summary</h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div><dt className="text-sm font-semibold">Stable ID</dt><dd>{scenarioDetails.stable_id}</dd></div>
            <div><dt className="text-sm font-semibold">Active status</dt><dd>{scenarioDetails.active ? "Active" : "Inactive"}</dd></div>
            <div><dt className="text-sm font-semibold">Difficulty</dt><dd>{scenarioDetails.difficulty} of 5</dd></div>
            <div><dt className="text-sm font-semibold">Category</dt><dd>{scenarioDetails.category}</dd></div>
          </dl>
        </section>
        {scenarioDetails.versions.map((version) => (
          <section className="panel" key={version.version} aria-labelledby={`version-${version.version}-heading`}>
            <h2 id={`version-${version.version}-heading`} className="text-xl font-bold">Version {version.version}</h2>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div><dt className="text-sm font-semibold">Published status</dt><dd>{version.published ? "Published" : "Not published"}</dd></div>
              <div><dt className="text-sm font-semibold">Active status</dt><dd>{version.active ? "Active" : "Inactive"}</dd></div>
              <div><dt className="text-sm font-semibold">Health status</dt><dd>{version.health_status}</dd></div>
              <div><dt className="text-sm font-semibold">Learning Mode availability</dt><dd>{version.learning_mode_available ? "Available" : "Unavailable"}</dd></div>
              <div><dt className="text-sm font-semibold">Simulation Mode availability</dt><dd>{version.simulation_mode_available ? "Available" : "Unavailable"}</dd></div>
              <div><dt className="text-sm font-semibold">Validation result</dt><dd>{version.validation_result.valid ? "Valid" : "Invalid"} ({version.validation_result.status})</dd></div>
              <DefinitionList label="Skill tags" values={version.skill_tags} />
              <DefinitionList label="Allowed tools" values={version.allowed_tools} />
            </dl>
            <div className="mt-5 rounded border p-3">
              <h3 className="font-bold">Administrator-safe metadata</h3>
              <dl className="mt-2 grid gap-3 text-sm sm:grid-cols-2">
                <DefinitionList label="Learning objectives" values={version.metadata.learning_objectives} />
                <div><dt className="font-semibold">Definition hash</dt><dd className="break-all">{version.metadata.definition_hash}</dd></div>
                <div><dt className="font-semibold">Published at</dt><dd>{version.metadata.published_at || "Not published"}</dd></div>
                <div><dt className="font-semibold">Published by</dt><dd>{version.metadata.published_by || "Unknown"}</dd></div>
              </dl>
            </div>
          </section>
        ))}
      </main>
    );
  }

  if (selectedArticleKey && selectedArticle) {
    return (
      <main className="mx-auto max-w-4xl space-y-5 p-4 md:p-6">
        <button className="btn-secondary" type="button" onClick={clearDetails}>Back to Knowledge Base</button>
        <header>
          <p className="text-sm font-semibold text-blue-600">KNOWLEDGE BASE ARTICLE</p>
          <h1 className="text-3xl font-bold">{selectedArticle.title}</h1>
        </header>
        {editingArticle ? (
          <form className="panel grid gap-3" onSubmit={updateKnowledge}>
            <h2 className="text-xl font-bold">Edit article</h2>
            <label className="grid gap-1 font-semibold">Stable ID<input className="input-field" value={articleDraft.stable_id} disabled /></label>
            <label className="grid gap-1 font-semibold">Title<input className="input-field" required value={articleDraft.title} onChange={(event) => setArticleDraft({ ...articleDraft, title: event.target.value })} /></label>
            <label className="grid gap-1 font-semibold">Category<input className="input-field" required value={articleDraft.category} onChange={(event) => setArticleDraft({ ...articleDraft, category: event.target.value })} /></label>
            <label className="grid gap-1 font-semibold">Article state<select className="input-field" value={articleDraft.status} onChange={(event) => setArticleDraft({ ...articleDraft, status: event.target.value })}><option value="draft">Draft</option><option value="published">Published</option></select></label>
            <label className="grid gap-1 font-semibold">Content<textarea className="input-field min-h-48" required value={articleDraft.content} onChange={(event) => setArticleDraft({ ...articleDraft, content: event.target.value })} /></label>
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" type="submit">Save changes</button>
              <button className="btn-secondary" type="button" onClick={() => { setArticleDraft({ ...selectedArticle }); setSearchParams({ article: selectedArticle.stable_id }, { replace: true }); }}>Cancel</button>
            </div>
          </form>
        ) : (
          <article className="panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="font-semibold">{selectedArticle.category}</p><p className="text-sm">Status: {selectedArticle.status}</p></div>
              <button className="btn-primary" type="button" onClick={() => setSearchParams({ article: selectedArticle.stable_id, edit: "1" }, { replace: true })}>Edit article</button>
            </div>
            <div className="mt-5 whitespace-pre-wrap">{selectedArticle.content}</div>
          </article>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <header>
        <p className="text-sm font-semibold text-blue-600">ASSESSMENTS & LABS</p>
        <h1 className="text-3xl font-bold">Service Desk Lab</h1>
        <p className="text-slate-600 dark:text-slate-300">Private-beta scenario review, assignments, and deterministic event replay.</p>
      </header>
      {error ? <p className="rounded border border-red-400 p-3" role="alert">{error}</p> : null}
      <section className="grid gap-3 md:grid-cols-3">
        <div className="panel"><p>Published scenarios</p><p className="text-3xl font-bold">{health?.published_count ?? "—"}</p></div>
        <div className="panel"><p>Health</p><p className="text-3xl font-bold">{health?.valid ? "Passing" : "Pending"}</p></div>
        <div className="panel"><p>Assignments</p><p className="text-3xl font-bold">{assignments.length}</p></div>
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel">
          <h2 className="text-xl font-bold">Private beta enrollment</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Enrollment alone never enables student access; the student feature flag must also be on.</p>
          <form className="mt-3 flex flex-wrap gap-2" onSubmit={enroll}>
            <label className="sr-only" htmlFor="beta-student-id">Student ID</label>
            <input id="beta-student-id" className="input-field max-w-40" required min="1" type="number" value={betaStudentId} onChange={(event) => setBetaStudentId(event.target.value)} placeholder="Student ID" />
            <button className="btn-primary" type="submit">Add beta student</button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">{enrollments.map((item) => (
            <li className="flex flex-wrap items-center justify-between gap-2 rounded border p-2" key={item.id}>
              <span>Student {item.student_id} · {item.enabled && !item.removed_at ? "Active" : "Removed"}</span>
              {item.enabled && !item.removed_at ? <button className="btn-secondary" type="button" onClick={async () => { await removeAdminServiceDeskBetaEnrollment(item.student_id); await load(); }}>Remove enrollment</button> : null}
            </li>
          ))}</ul>
        </div>
        <div className="panel">
          <h2 className="text-xl font-bold">Assign scenario</h2>
          <form className="mt-3 flex flex-wrap gap-2" onSubmit={assign}>
            <label className="sr-only" htmlFor="student-id">Student ID</label>
            <input id="student-id" className="input-field max-w-40" required min="1" type="number" value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="Student ID" />
            <label className="sr-only" htmlFor="scenario-id">Scenario ID</label>
            <select id="scenario-id" className="input-field max-w-64" required value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}><option value="">Choose scenario</option>{scenarios.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
            <button className="btn-primary" type="submit">Assign learning mode</button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">{assignments.map((item) => (
            <li className="flex flex-wrap items-center justify-between gap-2 rounded border p-2" key={item.id}>
              <span>Student {item.student_id} · Scenario {item.scenario_id} · {item.mode}</span>
              <button className="btn-secondary" type="button" onClick={async () => { await deleteAdminServiceDeskAssignment(item.id); await load(); }}>Remove assignment</button>
            </li>
          ))}</ul>
        </div>
      </section>
      <section className="panel">
        <h2 className="text-xl font-bold">Scenarios and validation</h2>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">{scenarios.map((item) => (
          <li key={item.id} className="rounded border p-3">
            <strong>{item.title}</strong>
            <p className="text-sm">{item.stable_key} · {item.status}</p>
            <ul className="mt-2 space-y-1 text-sm">{item.versions?.map((version) => <li key={version.version_number}>Version {version.version_number} · {version.status} · {version.health_valid ? "Health passing" : "Health pending"}</li>)}</ul>
            <button className="btn-secondary mt-3" type="button" onClick={() => showScenario(item.stable_key)}>View details</button>
          </li>
        ))}</ul>
      </section>
      <section className="panel">
        <h2 className="text-xl font-bold">Knowledge Base</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Published articles are student-visible; drafts remain administrator-only.</p>
        <form className="mt-3 grid gap-2 md:grid-cols-2" onSubmit={createKnowledge}>
          <input aria-label="Knowledge article stable ID" className="input-field" required value={newArticle.stable_id} onChange={(event) => setNewArticle({ ...newArticle, stable_id: event.target.value })} placeholder="Stable ID" />
          <input aria-label="Knowledge article title" className="input-field" required value={newArticle.title} onChange={(event) => setNewArticle({ ...newArticle, title: event.target.value })} placeholder="Title" />
          <input aria-label="Knowledge article category" className="input-field" required value={newArticle.category} onChange={(event) => setNewArticle({ ...newArticle, category: event.target.value })} placeholder="Category" />
          <select aria-label="Knowledge article status" className="input-field" value={newArticle.status} onChange={(event) => setNewArticle({ ...newArticle, status: event.target.value })}><option value="draft">Draft</option><option value="published">Published</option></select>
          <textarea aria-label="Knowledge article content" className="input-field min-h-24 md:col-span-2" required value={newArticle.content} onChange={(event) => setNewArticle({ ...newArticle, content: event.target.value })} placeholder="Article content" />
          <button className="btn-primary w-fit" type="submit">Create article</button>
        </form>
        <ul className="mt-4 grid gap-2 md:grid-cols-2">{knowledge.map((article) => (
          <li className="rounded border p-3" key={article.id}>
            <strong>{article.title}</strong>
            <p className="text-sm">{article.category} · {article.status}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" type="button" onClick={() => showArticle(article.stable_id)}>View article</button>
              <button className="btn-secondary" type="button" onClick={() => setSearchParams({ article: article.stable_id, edit: "1" })}>Edit article</button>
            </div>
          </li>
        ))}</ul>
      </section>
      <section className="panel overflow-x-auto">
        <h2 className="text-xl font-bold">Attempts</h2>
        <table className="mt-3 w-full min-w-[620px] text-left text-sm">
          <thead><tr><th>ID</th><th>Student</th><th>Version</th><th>Mode</th><th>Result</th><th>Actions</th></tr></thead>
          <tbody>{attempts.map((item) => (
            <tr className="border-t" key={item.id}>
              <td className="py-2">{item.id}</td><td>{item.student_id}</td><td>{item.scenario_version_id}</td><td>{item.mode}</td><td>{item.status} · {item.score ?? 0}%</td>
              <td className="space-x-2 whitespace-nowrap">
                <button className="btn-secondary" type="button" onClick={() => showAttempt(item.id, "replay")}>View replay</button>
                <button className="btn-secondary" type="button" onClick={() => showAttempt(item.id, "grade")}>Grade details</button>
                {item.mode === "simulation" && item.status !== "in_progress" ? <button className="btn-secondary" type="button" onClick={() => reset(item.id)}>Reset attempt</button> : null}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </section>
      {replay ? (
        <section className="panel" aria-labelledby="attempt-details-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h2 id="attempt-details-heading" className="text-xl font-bold">Attempt {replay.attempt.id} {attemptPanel === "grade" ? "grade details" : "event replay"}</h2>
            <button className="btn-secondary" type="button" onClick={clearDetails}>Close attempt details</button>
          </div>
          <p className="mt-2">Score: {replay.grade?.overall_score ?? 0}% · {replay.grade?.passed ? "Passed" : "Not passed"}</p>
          {replay.grade ? (
            <div className="mt-3 rounded border p-3">
              <h3 className="font-bold">Grade breakdown</h3>
              <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
                <div><dt className="text-slate-500">Rubric</dt><dd>{replay.grade.rubric_version}</dd></div>
                <div><dt className="text-slate-500">Technical completion</dt><dd>{replay.grade.technical_complete ? "Complete" : "Incomplete"}</dd></div>
                <div><dt className="text-slate-500">Critical failure</dt><dd>{replay.grade.critical_failure ? "Yes" : "No"}</dd></div>
              </dl>
              <p className="mt-2 text-sm"><strong>Earned scoring events:</strong> {(replay.grade.details?.earned_score_keys || []).join(", ") || "None"}</p>
            </div>
          ) : null}
          {attemptPanel === "replay" ? <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">{replay.events.map((event) => <li key={event.sequence_number}><strong>{event.tool}</strong> · {event.event_type} · {event.success ? "accepted" : "rejected"}</li>)}</ol> : null}
        </section>
      ) : null}
    </main>
  );
}
