import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { StatusBadge } from "../../components/ui/Badge";
import PageHeader from "../../components/ui/PageHeader";
import {
  createAdminCapstoneTemplate,
  deleteAdminCapstoneTemplate,
  getAdminCapstoneTemplates,
  updateAdminCapstoneTemplate,
} from "../../services/api";

const emptyForm = {
  title: "",
  description: "",
  role_level: "",
  week_number: "1",
  estimated_hours: "",
  is_published: false,
  requirements: "{}",
  deliverables: "{}",
  rubric: "{}",
};

const jsonFields = ["requirements", "deliverables", "rubric"];

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

export default function AdminCapstonesPage() {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await getAdminCapstoneTemplates();
      setTemplates(res.data || []);
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
      role_level: template.role_level == null ? "" : String(template.role_level),
      week_number: template.week_number == null ? "" : String(template.week_number),
      estimated_hours: template.estimated_hours == null ? "" : String(template.estimated_hours),
      is_published: !!template.is_published,
      requirements: formatJson(template.requirements),
      deliverables: formatJson(template.deliverables),
      rubric: formatJson(template.rubric),
    });
    setEditingId(template.id);
    setShowForm(true);
    setError("");
  };

  const buildPayload = () => {
    const roleLevel = toNullableNumber(form.role_level);
    if (Number.isNaN(roleLevel)) {
      throw new Error("Role level must be a numeric role id.");
    }

    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      role_level: roleLevel,
      week_number: toNullableNumber(form.week_number),
      estimated_hours: toNullableNumber(form.estimated_hours),
      is_published: form.is_published,
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
      setError(err instanceof SyntaxError ? `Invalid JSON: ${err.message}` : err.message);
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await updateAdminCapstoneTemplate(editingId, payload);
      } else {
        await createAdminCapstoneTemplate(payload);
      }
      await loadTemplates();
      resetForm();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (template) => {
    if (!window.confirm(`Delete capstone template "${template.title}"?`)) return;
    await deleteAdminCapstoneTemplate(template.id);
    await loadTemplates();
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader
        title="Capstone Templates"
        actions={
          <button className="btn-primary gap-2" type="button" onClick={startCreate}>
            <Plus size={16} aria-hidden="true" />
            Create New Capstone
          </button>
        }
      />

      {showForm ? (
        <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">{editingId ? "Edit Capstone" : "Create Capstone"}</h2>
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
                <span>Role Level</span>
                <input
                  className="input-field"
                  type="text"
                  value={form.role_level}
                  onChange={(event) => setField("role_level", event.target.value)}
                />
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
                <span>Estimated Hours</span>
                <input
                  className="input-field"
                  type="number"
                  min="0"
                  value={form.estimated_hours}
                  onChange={(event) => setField("estimated_hours", event.target.value)}
                />
              </label>
              <label className="flex items-center gap-2 text-sm font-medium md:col-span-2">
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

            <div className="grid gap-4 md:grid-cols-3">
              {jsonFields.map((field) => (
                <label key={field} className="space-y-1 text-sm font-medium">
                  <span>{field}</span>
                  <textarea
                    className="input-field min-h-44 font-mono"
                    value={form[field]}
                    onChange={(event) => setField(field, event.target.value)}
                  />
                </label>
              ))}
            </div>

            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update Capstone" : "Create Capstone"}
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
                <th className="px-4 py-3 font-semibold">Role Level</th>
                <th className="px-4 py-3 font-semibold">Week</th>
                <th className="px-4 py-3 font-semibold">Hours</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="px-4 py-6 text-slate-500 dark:text-slate-400" colSpan={6}>
                    Loading capstone templates...
                  </td>
                </tr>
              ) : null}
              {!loading && templates.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-slate-500 dark:text-slate-400" colSpan={6}>
                    No capstone templates found.
                  </td>
                </tr>
              ) : null}
              {!loading
                ? templates.map((template) => (
                    <tr key={template.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">{template.title}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.role_level || "-"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.week_number || "-"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{template.estimated_hours || "-"}</td>
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
    </main>
  );
}
