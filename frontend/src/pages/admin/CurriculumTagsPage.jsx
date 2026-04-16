import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import Spinner from "../../components/Spinner";
import { getAdminCurriculumVideos, updateAdminCurriculumVideoTag } from "../../services/api";

const TAG_OPTIONS = [
  { value: "job_critical", label: "💼 Job Critical" },
  { value: "know_it", label: "📚 Know It" },
  { value: "awareness", label: "👀 Awareness Only" },
];

export default function CurriculumTagsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingById, setSavingById] = useState({});
  const [savedById, setSavedById] = useState({});

  useEffect(() => {
    const run = async () => {
      try {
        const res = await getAdminCurriculumVideos({ suppressToast: true });
        setRows(res?.data || []);
      } catch {
        toast.error("Failed to load curriculum tags");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  const grouped = useMemo(() => {
    const map = {};
    rows.forEach((row) => {
      if (!map[row.section]) map[row.section] = [];
      map[row.section].push(row);
    });
    return map;
  }, [rows]);

  const counts = useMemo(() => {
    const c = { job_critical: 0, know_it: 0, awareness: 0 };
    rows.forEach((row) => {
      if (c[row.job_relevance] != null) c[row.job_relevance] += 1;
    });
    return c;
  }, [rows]);

  const onChangeTag = async (id, jobRelevance) => {
    setSavingById((prev) => ({ ...prev, [id]: true }));
    setSavedById((prev) => ({ ...prev, [id]: false }));

    const previous = rows;
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, job_relevance: jobRelevance } : row)));

    try {
      await updateAdminCurriculumVideoTag(id, { job_relevance: jobRelevance }, { suppressToast: true });
      setSavedById((prev) => ({ ...prev, [id]: true }));
      setTimeout(() => setSavedById((prev) => ({ ...prev, [id]: false })), 1500);
    } catch {
      setRows(previous);
      toast.error("Save failed");
    } finally {
      setSavingById((prev) => ({ ...prev, [id]: false }));
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <Spinner text="Loading tags..." />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Curriculum Job Relevance Tags</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {counts.job_critical} Job Critical · {counts.know_it} Know It · {counts.awareness} Awareness
        </p>
      </div>

      {Object.entries(grouped).map(([section, sectionRows]) => (
        <section key={section} className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <header className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
            {section}
          </header>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-2 text-left font-medium">Video Title</th>
                  <th className="px-4 py-2 text-left font-medium">Section</th>
                  <th className="px-4 py-2 text-left font-medium">Current Tag</th>
                </tr>
              </thead>
              <tbody>
                {sectionRows.map((row) => (
                  <tr key={row.id} className="border-b border-slate-50 dark:border-slate-800/50">
                    <td className="px-4 py-2 text-slate-800 dark:text-slate-200">{row.title}</td>
                    <td className="px-4 py-2 text-slate-500 dark:text-slate-400">{row.section}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <select
                          className="input-field max-w-56"
                          value={row.job_relevance}
                          onChange={(e) => onChangeTag(row.id, e.target.value)}
                          disabled={!!savingById[row.id]}
                        >
                          {TAG_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {savingById[row.id] ? "Saving..." : savedById[row.id] ? "Saved" : ""}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </main>
  );
}
