import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Eye, Plus, Save, Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  addAdminTrainingActivity,
  createAdminTrainingWeek,
  deleteAdminTrainingActivity,
  getAdminTrainingValidation,
  getAdminTrainingQuizOptions,
  getAdminTrainingWeeks,
  reorderAdminTrainingActivities,
  reorderAdminTrainingWeeks,
  updateAdminTrainingActivity,
  updateAdminTrainingWeek,
} from "../../services/api";

const activityTypes = [
  "video", "quiz", "lesson", "guided_lab", "networking_lab",
  "service_desk_scenario", "command_exercise", "terminal_exercise", "review", "capstone",
];
const emptyActivity = {
  activity_type: "video", content_ref: "", is_required: true,
  estimated_minutes: "", prerequisite_activity_id: "", prerequisite_mode: "soft",
  quiz_id: "", quiz_mapping_basis: "topic_group",
};

const mappingLabels = {
  exact: "Exact",
  topic_group: "Strong topical",
  week_fallback: "Week-level fallback",
};

function moveItem(items, index, direction) {
  const destination = index + direction;
  if (destination < 0 || destination >= items.length) return items;
  const next = [...items];
  [next[index], next[destination]] = [next[destination], next[index]];
  return next;
}

export default function AdminTrainingPage() {
  const [weeks, setWeeks] = useState([]);
  const [validation, setValidation] = useState(null);
  const [quizOptions, setQuizOptions] = useState([]);
  const [openWeek, setOpenWeek] = useState(null);
  const [draft, setDraft] = useState(emptyActivity);
  const [newWeek, setNewWeek] = useState({ week_number: "", title: "", description: "" });
  const [message, setMessage] = useState("");

  const load = async () => {
    const [weekRes, validationRes, quizRes] = await Promise.all([
      getAdminTrainingWeeks(), getAdminTrainingValidation(), getAdminTrainingQuizOptions(),
    ]);
    setWeeks(weekRes.data || []);
    setValidation(validationRes.data);
    setQuizOptions(quizRes.data || []);
  };
  useEffect(() => { load().catch(() => setMessage("Training curriculum could not be loaded.")); }, []);

  const patchWeek = (id, values) => setWeeks((items) =>
    items.map((item) => (item.id === id ? { ...item, ...values } : item)));

  const saveWeek = async (week) => {
    await updateAdminTrainingWeek(week.id, {
      title: week.title,
      description: week.description,
      estimated_minutes: week.estimated_minutes,
      is_active: week.is_active,
      requires_previous_week: week.requires_previous_week,
    });
    setMessage(`Saved Week ${week.week_number}.`);
    await load();
  };

  const createWeek = async () => {
    await createAdminTrainingWeek({
      week_number: Number(newWeek.week_number),
      title: newWeek.title,
      description: newWeek.description || null,
      learning_goals: [],
      is_active: true,
      requires_previous_week: Number(newWeek.week_number) > 0,
    });
    setNewWeek({ week_number: "", title: "", description: "" });
    setMessage("Training week created.");
    await load();
  };

  const addActivity = async (week) => {
    const { quiz_id: quizId, quiz_mapping_basis: mappingBasis, ...activityDraft } = draft;
    await addAdminTrainingActivity(week.id, {
      ...activityDraft,
      stable_id: `week-${week.week_number}-${draft.activity_type}-${draft.content_ref}`,
      estimated_minutes: draft.estimated_minutes ? Number(draft.estimated_minutes) : null,
      prerequisite_activity_id: draft.prerequisite_activity_id ? Number(draft.prerequisite_activity_id) : null,
      metadata_json: draft.activity_type === "video" ? {
        quiz_id: Number(quizId),
        quiz_mapping_basis: mappingBasis,
        quiz_mapping_confidence: mappingLabels[mappingBasis],
        quiz_mapping_evidence: "Administrator-reviewed curriculum mapping.",
      } : {},
    });
    setDraft(emptyActivity);
    setMessage("Activity added.");
    await load();
  };

  const updateVideoMapping = async (activity, values) => {
    const metadata = { ...(activity.metadata_json || {}), ...values };
    metadata.quiz_id = Number(metadata.quiz_id);
    metadata.quiz_mapping_confidence = mappingLabels[metadata.quiz_mapping_basis];
    metadata.quiz_mapping_evidence = "Administrator-reviewed curriculum mapping.";
    await updateAdminTrainingActivity(activity.id, { metadata_json: metadata });
    setMessage(`Saved quiz mapping for ${activity.stable_id}.`);
    await load();
  };

  const moveWeek = async (index, direction) => {
    const ordered = moveItem(weeks, index, direction);
    if (ordered === weeks) return;
    await reorderAdminTrainingWeeks(ordered.map((week, order) => ({ id: week.id, display_order: order })));
    await load();
  };

  const moveActivity = async (week, index, direction) => {
    const ordered = moveItem(week.activities, index, direction);
    if (ordered === week.activities) return;
    await reorderAdminTrainingActivities(ordered.map((activity, order) => ({ id: activity.id, display_order: order + 1 })));
    await load();
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 pb-20 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-blue-600">Learning Content</p>
          <h1 className="mt-1 text-3xl font-bold">Weekly Training</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">Reference existing content, set order and requirements, and validate links.</p>
        </div>
        {validation ? (
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-bold ${validation.valid ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
            {validation.valid ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            {validation.valid ? "References valid" : `${validation.issues.filter((item) => item.severity === "error").length} errors`}
          </span>
        ) : null}
      </div>

      {message ? <p role="status" className="rounded-xl bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-950/30 dark:text-blue-200">{message}</p> : null}

      {validation ? <section className="panel flex flex-wrap gap-x-6 gap-y-2 text-sm"><span><strong>{validation.mapped_video_count} of {validation.enabled_video_count}</strong> enabled videos mapped</span><span><strong>{validation.mapping_summary?.Exact || 0}</strong> exact</span><span><strong>{validation.mapping_summary?.["Strong topical"] || 0}</strong> topic-group</span><span><strong>{validation.mapping_summary?.["Week-level fallback"] || 0}</strong> week fallback</span></section> : null}

      <section className="panel">
        <h2 className="font-bold">Create a week</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-[8rem_1fr_2fr_auto]">
          <input className="input-field" type="number" min="0" placeholder="Week #" value={newWeek.week_number} onChange={(event) => setNewWeek({ ...newWeek, week_number: event.target.value })} />
          <input className="input-field" placeholder="Title" value={newWeek.title} onChange={(event) => setNewWeek({ ...newWeek, title: event.target.value })} />
          <input className="input-field" placeholder="Short description" value={newWeek.description} onChange={(event) => setNewWeek({ ...newWeek, description: event.target.value })} />
          <button className="btn-primary disabled:opacity-50" disabled={newWeek.week_number === "" || !newWeek.title.trim()} onClick={createWeek} type="button"><Plus size={15} />Create</button>
        </div>
      </section>

      {validation?.issues?.length ? (
        <section className="panel">
          <h2 className="font-bold">Curriculum validation</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {validation.issues.map((issue, index) => (
              <li key={`${issue.code}-${index}`} className={issue.severity === "error" ? "text-red-700 dark:text-red-300" : "text-amber-700 dark:text-amber-300"}>
                Week {issue.week_number}: {issue.message}{issue.stable_id ? ` (${issue.stable_id})` : ""}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="space-y-3">
        {weeks.map((week, weekIndex) => (
          <section key={week.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1 p-2">
              <button aria-label={`Move Week ${week.week_number} up`} className="rounded p-2 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800" disabled={weekIndex === 0} onClick={() => moveWeek(weekIndex, -1)} type="button"><ChevronUp size={16} /></button>
              <button aria-label={`Move Week ${week.week_number} down`} className="rounded p-2 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-slate-800" disabled={weekIndex === weeks.length - 1} onClick={() => moveWeek(weekIndex, 1)} type="button"><ChevronDown size={16} /></button>
              <button type="button" onClick={() => setOpenWeek(openWeek === week.id ? null : week.id)} className="flex flex-1 items-center justify-between gap-3 rounded-lg p-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800">
                <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Week {week.week_number} · {week.activities.length} activities · {week.is_active ? "Enabled" : "Disabled"}</p><h2 className="mt-1 text-lg font-bold">{week.title}</h2></div>
                {openWeek === week.id ? <ChevronUp /> : <ChevronDown />}
              </button>
            </div>

            {openWeek === week.id ? (
              <div className="space-y-5 border-t border-slate-200 p-4 dark:border-slate-700">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm font-semibold">Title<input className="input-field mt-1 w-full" value={week.title} onChange={(event) => patchWeek(week.id, { title: event.target.value })} /></label>
                  <label className="text-sm font-semibold">Estimated minutes<input type="number" min="0" className="input-field mt-1 w-full" value={week.estimated_minutes || ""} onChange={(event) => patchWeek(week.id, { estimated_minutes: Number(event.target.value) || null })} /></label>
                  <label className="text-sm font-semibold md:col-span-2">Description<textarea className="input-field mt-1 min-h-20 w-full" value={week.description || ""} onChange={(event) => patchWeek(week.id, { description: event.target.value })} /></label>
                  <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={week.is_active} onChange={(event) => patchWeek(week.id, { is_active: event.target.checked })} />Enabled</label>
                  <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={week.requires_previous_week} onChange={(event) => patchWeek(week.id, { requires_previous_week: event.target.checked })} />Require previous week</label>
                </div>
                <div className="flex flex-wrap gap-2"><button className="btn-primary" type="button" onClick={() => saveWeek(week)}><Save size={15} />Save week</button><Link className="btn-secondary" to={`/training/week/${week.week_number}`} target="_blank"><Eye size={15} />Preview as student</Link></div>

                <div>
                  <h3 className="font-bold">Activities</h3>
                  <div className="mt-2 overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead><tr className="border-b text-left text-slate-500"><th className="p-2">Order</th><th className="p-2">Type</th><th className="p-2">Referenced ID</th><th className="p-2">Mapped quiz</th><th className="p-2">Required</th><th className="p-2">Prerequisite</th><th className="p-2"><span className="sr-only">Actions</span></th></tr></thead>
                      <tbody>{week.activities.map((activity, activityIndex) => (
                        <tr key={activity.id} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="whitespace-nowrap p-2"><button aria-label="Move activity up" disabled={activityIndex === 0} onClick={() => moveActivity(week, activityIndex, -1)} className="p-1 disabled:opacity-30" type="button">↑</button><button aria-label="Move activity down" disabled={activityIndex === week.activities.length - 1} onClick={() => moveActivity(week, activityIndex, 1)} className="p-1 disabled:opacity-30" type="button">↓</button> {activity.display_order}</td>
                          <td className="p-2">{activity.activity_type}</td><td className="p-2 font-mono">{activity.content_ref}</td>
                          <td className="p-2">{activity.activity_type === "video" ? <div className="grid min-w-56 gap-1"><select aria-label={`Quiz for ${activity.stable_id}`} className="input-field text-xs" value={activity.metadata_json?.quiz_id || ""} onChange={(event) => updateVideoMapping(activity, { quiz_id: event.target.value })}><option value="" disabled>Select approved quiz</option>{quizOptions.map((quiz) => <option key={quiz.id} value={quiz.id}>W{quiz.week_number}: {quiz.title}</option>)}</select><select aria-label={`Mapping basis for ${activity.stable_id}`} className="input-field text-xs" value={activity.metadata_json?.quiz_mapping_basis || "topic_group"} onChange={(event) => updateVideoMapping(activity, { quiz_mapping_basis: event.target.value })}><option value="exact">Exact</option><option value="topic_group">Topic group</option><option value="week_fallback">Week fallback</option></select></div> : <span className="text-slate-400">—</span>}</td>
                          <td className="p-2"><input aria-label={`Required ${activity.stable_id}`} type="checkbox" checked={activity.is_required} onChange={async (event) => { await updateAdminTrainingActivity(activity.id, { is_required: event.target.checked }); await load(); }} /></td>
                          <td className="p-2"><input aria-label={`Prerequisite for ${activity.stable_id}`} className="input-field w-24" type="number" placeholder="Activity ID" value={activity.prerequisite_activity_id || ""} onChange={async (event) => { await updateAdminTrainingActivity(activity.id, { prerequisite_activity_id: event.target.value ? Number(event.target.value) : null }); await load(); }} /></td>
                          <td className="p-2 text-right"><button aria-label={`Remove ${activity.stable_id}`} className="rounded p-2 text-red-600 hover:bg-red-50" type="button" onClick={async () => { await deleteAdminTrainingActivity(activity.id); await load(); }}><Trash2 size={15} /></button></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                </div>

                <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
                  <h3 className="font-bold">Add existing activity</h3>
                  <div className="mt-2 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
                    <select className="input-field" value={draft.activity_type} onChange={(event) => setDraft({ ...draft, activity_type: event.target.value })}>{activityTypes.map((type) => <option key={type}>{type}</option>)}</select>
                    <input className="input-field" placeholder="Content ID" value={draft.content_ref} onChange={(event) => setDraft({ ...draft, content_ref: event.target.value })} />
                    <input className="input-field" type="number" min="0" placeholder="Minutes" value={draft.estimated_minutes} onChange={(event) => setDraft({ ...draft, estimated_minutes: event.target.value })} />
                    <input className="input-field" type="number" placeholder="Prerequisite activity ID" value={draft.prerequisite_activity_id} onChange={(event) => setDraft({ ...draft, prerequisite_activity_id: event.target.value })} />
                    <select className="input-field" value={draft.prerequisite_mode} onChange={(event) => setDraft({ ...draft, prerequisite_mode: event.target.value })}><option value="soft">Soft prerequisite</option><option value="hard">Hard prerequisite</option></select>
                    <button disabled={!draft.content_ref || (draft.activity_type === "video" && !draft.quiz_id)} className="btn-primary disabled:opacity-50" type="button" onClick={() => addActivity(week)}><Plus size={15} />Add</button>
                  </div>
                  {draft.activity_type === "video" ? <div className="mt-2 grid gap-2 sm:grid-cols-2"><label className="text-sm font-semibold">Mapped quiz<select className="input-field mt-1 w-full" value={draft.quiz_id} onChange={(event) => setDraft({ ...draft, quiz_id: event.target.value })}><option value="">Select an approved quiz</option>{quizOptions.map((quiz) => <option key={quiz.id} value={quiz.id}>Week {quiz.week_number} — {quiz.title}</option>)}</select></label><label className="text-sm font-semibold">Mapping basis<select className="input-field mt-1 w-full" value={draft.quiz_mapping_basis} onChange={(event) => setDraft({ ...draft, quiz_mapping_basis: event.target.value })}><option value="exact">Exact</option><option value="topic_group">Topic group</option><option value="week_fallback">Week fallback</option></select></label></div> : null}
                  <label className="mt-2 inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.is_required} onChange={(event) => setDraft({ ...draft, is_required: event.target.checked })} />Required</label>
                </div>
              </div>
            ) : null}
          </section>
        ))}
      </div>
    </main>
  );
}
