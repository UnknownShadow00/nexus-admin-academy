import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { StatusBadge } from "../../components/ui/Badge";
import PageHeader from "../../components/ui/PageHeader";
import {
  createAdminLabTemplate,
  deleteAdminLabTemplate,
  getAdminLabTemplates,
  getAdminVmAssignments,
  updateAdminLabTemplate,
} from "../../services/api";

const emptyForm = {
  title: "",
  description: "",
  lab_type: "",
  difficulty: "1",
  week_number: "1",
  estimated_minutes: "",
  is_published: false,
  proxmox_template_vmid: "",
  setup_instructions: "",
  break_script: "",
  model_solution: "",
  success_criteria: "{}",
  required_evidence: "{}",
  hints: "{}",
  environment_requirements: "{}",
};

const jsonFields = ["success_criteria", "required_evidence", "hints", "environment_requirements"];

function formatJson(value) {
  return JSON.stringify(value || {}, null, 2);
}

function parseJsonField(form, field) {
  const raw = form[field].trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

function toNullableNumber(value) {
  return value === "" || value == null ? null : Number(value);
}

export default function AdminLabsPage() {
  const [templates, setTemplates] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const [templatesRes, assignmentsRes] = await Promise.all([
        getAdminLabTemplates(),
        getAdminVmAssignments(),
      ]);
      setTemplates(templatesRes.data || []);
      setAssignments(assignmentsRes.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(false);
    setError("");
  };

  const startCreate = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(true);
    setError("");
  };

  const startEdit = (template) => {
    setForm({
      title: template.title || "",
      description: template.description || "",
      lab_type: template.lab_type || "",
      difficulty: String(template.difficulty || 1),
      week_number: String(template.week_number || 1),
      estimated_minutes: template.estimated_minutes == null ? "" : String(template.estimated_minutes),
      is_published: !!template.is_published,
      proxmox_template_vmid: template.proxmox_template_vmid == null ? "" : String(template.proxmox_template_vmid),
      setup_instructions: template.setup_instructions || "",
      break_script: template.break_script || "",
      model_solution: template.model_solution || "",
      success_criteria: formatJson(template.success_criteria),
      required_evidence: formatJson(template.required_evidence),
      hints: formatJson(template.hints),
      environment_requirements: formatJson(template.environment_requirements),
    });
    setEditingId(template.id);
    setShowForm(true);
    setError("");
  };

  const buildPayload = () => {
    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      lab_type: form.lab_type.trim() || null,
      difficulty: Number(form.difficulty || 1),
      week_number: Number(form.week_number || 1),
      estimated_minutes: toNullableNumber(form.estimated_minutes),
      is_published: form.is_published,
      proxmox_template_vmid: toNullableNumber(form.proxmox_template_vmid),
      setup_instructions: form.setup_instructions.trim() || null,
      break_script: form.break_script.trim() || null,
      model_solution: form.model_solution.trim() || null,
    };

    jsonFields.forEach((field) => {
      payload[field] = parseJsonField(form, field);
    });

    return payload;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    if (!form.title.trim()) {
      setError("Title is required.");
      return;
    }

    let payload;
    try {
      payload = buildPayload();
    } catch (err) {
      setError(`Invalid JSON: ${err.message}`);
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await updateAdminLabTemplate(editingId, payload);
      } else {
        await createAdminLabTemplate(payload);
      }
      await loadTemplates();
      resetForm();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (template) => {
    if (!window.confirm(`Delete lab template "${template.title}"?`)) return;
    await deleteAdminLabTemplate(template.id);
    await loadTemplates();
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader
        title="Lab Templates"
        actions={
          <button className="btn-primary gap-2" type="button" onClick={startCreate}>
            <Plus size={16} aria-hidden="true" />
            Create New Lab
          </button>
        }
      />

      {showForm ? (
        <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{editingId ? "Edit Lab" : "Create Lab"}</h2>
            <button className="btn-secondary gap-2" type="button" onClick={resetForm}>
              <X size={16} aria-hidden="true" />
              Cancel
            </button>
          </div>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
              {error}
            </div>
          ) : null}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm font-medium">
                <span>Title</span>
                <input
                  className="input-field"
                  required
                  value={form.title}
                  onChange={(event) => setField("title", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Lab Type</span>
                <input
                  className="input-field"
                  placeholder="windows"
                  value={form.lab_type}
                  onChange={(event) => setField("lab_type", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Difficulty</span>
                <select
                  className="input-field"
                  value={form.difficulty}
                  onChange={(event) => setField("difficulty", event.target.value)}
                >
                  {[1, 2, 3, 4, 5].map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Week Number</span>
                <input
                  className="input-field"
                  type="number"
                  min="1"
                  value={form.week_number}
                  onChange={(event) => setField("week_number", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Estimated Minutes</span>
                <input
                  className="input-field"
                  type="number"
                  min="0"
                  value={form.estimated_minutes}
                  onChange={(event) => setField("estimated_minutes", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Proxmox Template VMID</span>
                <input
                  className="input-field"
                  type="number"
                  min="1"
                  placeholder="Leave blank for non-VM labs"
                  value={form.proxmox_template_vmid}
                  onChange={(event) => setField("proxmox_template_vmid", event.target.value)}
                />
              </label>
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700"
                  type="checkbox"
                  checked={form.is_published}
                  onChange={(event) => setField("is_published", event.target.checked)}
                />
                <span>Published</span>
              </label>
            </div>

            <label className="space-y-1 text-sm font-medium">
              <span>Description</span>
              <textarea
                className="input-field min-h-24"
                value={form.description}
                onChange={(event) => setField("description", event.target.value)}
              />
            </label>

            <div className="grid gap-4 lg:grid-cols-3">
              <label className="space-y-1 text-sm font-medium">
                <span>Setup Instructions</span>
                <textarea
                  className="input-field min-h-36"
                  value={form.setup_instructions}
                  onChange={(event) => setField("setup_instructions", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Break Script</span>
                <textarea
                  className="input-field min-h-36 font-mono"
                  value={form.break_script}
                  onChange={(event) => setField("break_script", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium">
                <span>Model Solution</span>
                <textarea
                  className="input-field min-h-36"
                  value={form.model_solution}
                  onChange={(event) => setField("model_solution", event.target.value)}
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {jsonFields.map((field) => (
                <label key={field} className="space-y-1 text-sm font-medium">
                  <span>{field}</span>
                  <textarea
                    className="input-field min-h-36 font-mono"
                    value={form[field]}
                    onChange={(event) => setField(field, event.target.value)}
                  />
                </label>
              ))}
            </div>

            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update Lab" : "Create Lab"}
            </button>
          </form>
        </section>
      ) : null}

      <section className="panel overflow-hidden p-0 dark:border-slate-700 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3 font-semibold">Title</th>
                <th className="px-4 py-3 font-semibold">Type</th>
                <th className="px-4 py-3 font-semibold">Difficulty</th>
                <th className="px-4 py-3 font-semibold">Week</th>
                <th className="px-4 py-3 font-semibold">VM Template</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="px-4 py-6 text-slate-500 dark:text-slate-400" colSpan={7}>
                    Loading lab templates...
                  </td>
                </tr>
              ) : null}
              {!loading && templates.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-slate-500 dark:text-slate-400" colSpan={7}>
                    No lab templates found.
                  </td>
                </tr>
              ) : null}
              {!loading
                ? templates.map((template) => (
                    <tr key={template.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{template.title}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.lab_type || "-"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.difficulty}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.week_number}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.proxmox_template_vmid || "-"}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={template.is_published ? "published" : "draft"} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button className="btn-secondary gap-2" type="button" onClick={() => startEdit(template)}>
                            <Pencil size={16} aria-hidden="true" />
                            Edit
                          </button>
                          <button className="btn-danger gap-2" type="button" onClick={() => handleDelete(template)}>
                            <Trash2 size={16} aria-hidden="true" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">VM Assignments</h2>
        {assignments.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No VM assignments found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="px-3 py-2 font-semibold">Student</th>
                  <th className="px-3 py-2 font-semibold">Lab</th>
                  <th className="px-3 py-2 font-semibold">VMID</th>
                  <th className="px-3 py-2 font-semibold">Status</th>
                  <th className="px-3 py-2 font-semibold">Failure</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((assignment) => (
                  <tr key={assignment.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="px-3 py-2">{assignment.student_name}</td>
                    <td className="px-3 py-2">{assignment.lab_title}</td>
                    <td className="px-3 py-2">{assignment.vmid || "-"}</td>
                    <td className="px-3 py-2"><StatusBadge status={assignment.status} /></td>
                    <td className="px-3 py-2 text-red-600 dark:text-red-300">{assignment.provisioning_error || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
