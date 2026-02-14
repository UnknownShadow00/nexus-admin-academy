import { useEffect, useMemo, useState } from "react";
import EmptyState from "../components/EmptyState";
import TerminalWidget from "../components/Terminal";
import { getResources } from "../services/api";

const iconByType = {
  Video: "[VID]",
  Article: "[DOC]",
  "Study Guide": "[GUIDE]",
  Other: "[RES]",
};

export default function ResourcesPage() {
  const [week, setWeek] = useState("");
  const [type, setType] = useState("");
  const [category, setCategory] = useState("");
  const [items, setItems] = useState([]);

  useEffect(() => {
    const run = async () => {
      const res = await getResources({ week: week || undefined, type: type || undefined, category: category || undefined });
      setItems(res.data || []);
    };
    run();
  }, [week, type, category]);

  const categories = useMemo(() => [...new Set(items.map((x) => x.category).filter(Boolean))], [items]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Resources Library</h1>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <input className="input-field" type="number" placeholder="Week" value={week} onChange={(e) => setWeek(e.target.value)} />
          <select className="input-field" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">All types</option>
            <option value="Video">Video</option>
            <option value="Article">Article</option>
            <option value="Study Guide">Study Guide</option>
            <option value="Other">Other</option>
          </select>
          <select className="input-field" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-xl font-bold">Practice Commands</h2>
        <TerminalWidget />
      </section>

      {!items.length ? (
        <EmptyState icon=".." title="No resources added yet" message="Your instructor will add study materials soon" />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="panel dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{iconByType[item.resource_type] || "[RES]"} {item.title}</h3>
                <a className="btn-secondary" href={item.url} target="_blank" rel="noreferrer">Open Resource</a>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Week {item.week_number} - {item.resource_type} - {item.category || "General"}</p>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
