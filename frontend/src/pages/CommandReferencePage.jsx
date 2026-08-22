import { useEffect, useMemo, useState } from "react";
import BackLink from "../components/BackLink";
import Banner from "../components/ui/Banner";
import FilterBar from "../components/ui/FilterBar";
import PageHeader from "../components/ui/PageHeader";
import { getCommands } from "../services/api";

const osFilters = ["all", "windows", "linux", "both"];
const buttonBase = "rounded-lg px-3 py-2 text-sm font-semibold transition-colors";
const buttonActive = "bg-blue-600 text-white";
const buttonInactive = "border border-slate-300 bg-white text-slate-700 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

function FilterButton({ active, children, onClick }) {
  return (
    <button className={`${buttonBase} ${active ? buttonActive : buttonInactive}`} onClick={onClick} type="button">
      {children}
    </button>
  );
}

function BadgePill({ children }) {
  return (
    <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
      {children}
    </span>
  );
}

export default function CommandReferencePage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [os, setOs] = useState("all");
  const [category, setCategory] = useState("all");
  const [commands, setCommands] = useState([]);
  const [categories, setCategories] = useState(["all"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const params = {
          search: search || undefined,
          os: os === "all" ? undefined : os,
          category: category === "all" ? undefined : category,
        };
        const res = await getCommands(params, { suppressToast: true });
        if (cancelled) return;
        const rows = Array.isArray(res.data) ? res.data : [];
        setCommands(rows);
        const nextCategories = Array.isArray(res.categories) && res.categories.length ? res.categories : rows.map((row) => row.category || "general");
        setCategories(["all", ...Array.from(new Set(nextCategories)).sort()]);
      } catch (err) {
        if (!cancelled) {
          setCommands([]);
          setError(err?.userMessage || "Unable to load commands.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [category, os, search]);

  const countText = useMemo(() => {
    if (loading) return "Loading commands...";
    return `${commands.length} command${commands.length === 1 ? "" : "s"}`;
  }, [commands.length, loading]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <BackLink fallbackLabel="Labs" fallbackTo="/labs" />
      <PageHeader title="Command Library" subtitle={countText} />

      <FilterBar>
        <div className="min-w-64 flex-1">
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Search</label>
          <input
            className="input-field"
            placeholder="Search commands, syntax, or examples..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">OS</p>
          <div className="flex flex-wrap gap-2">
            {osFilters.map((item) => (
              <FilterButton key={item} active={os === item} onClick={() => setOs(item)}>
                {item}
              </FilterButton>
            ))}
          </div>
        </div>
        <div className="min-w-full">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Category</p>
          <div className="flex flex-wrap gap-2">
            {categories.map((item) => (
              <FilterButton key={item} active={category === item} onClick={() => setCategory(item)}>
                {item}
              </FilterButton>
            ))}
          </div>
        </div>
      </FilterBar>

      {error ? <Banner variant="error">{error}</Banner> : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {loading
          ? [1, 2, 3, 4, 5, 6].map((id) => (
              <div key={id} className="panel animate-pulse dark:border-slate-700 dark:bg-slate-900">
                <div className="h-5 w-32 rounded bg-slate-200 dark:bg-slate-700" />
                <div className="mt-3 h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
                <div className="mt-2 h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
              </div>
            ))
          : commands.map((command) => (
              <article key={command.id} className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <code className="rounded bg-slate-950 px-2 py-1 font-mono text-sm font-semibold text-slate-50 dark:bg-slate-800">
                    {command.command}
                  </code>
                  <div className="flex flex-wrap gap-2">
                    <BadgePill>{command.category || "general"}</BadgePill>
                    <BadgePill>{command.os || "both"}</BadgePill>
                  </div>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-300">{command.description}</p>
                {command.syntax ? (
                  <pre className="overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700 dark:bg-slate-950 dark:text-slate-200">
                    <code>{command.syntax}</code>
                  </pre>
                ) : null}
                {command.example ? <p className="text-xs text-slate-500 dark:text-slate-400">Example: {command.example}</p> : null}
              </article>
            ))}
      </section>

      {!loading && !commands.length && !error ? (
        <div className="panel text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          No commands match the current filters.
        </div>
      ) : null}
    </main>
  );
}
