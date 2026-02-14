import { useState } from "react";
import { Search, Terminal } from "lucide-react";
import EmptyState from "../components/EmptyState";
import { searchCommands } from "../services/api";

export default function CommandReference() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const response = await searchCommands(query);
      setResults(response.commands || []);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="mb-2 flex items-center gap-2 text-3xl font-bold">
          <Terminal size={32} />
          Command Reference
        </h1>
        <p className="text-slate-600 dark:text-slate-300">Search for Windows and PowerShell commands</p>
      </div>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 text-slate-400" size={20} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands (e.g., ipconfig, Get-Service)..."
              className="w-full rounded-lg border border-slate-300 py-3 pl-10 pr-4"
            />
          </div>
          <button type="submit" className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700">Search</button>
        </div>
      </form>

      {loading && <div className="py-8 text-center">Searching...</div>}

      <div className="space-y-4">
        {results.map((cmd) => (
          <div key={cmd.id} className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <h3 className="font-mono text-xl font-bold text-blue-600">{cmd.command}</h3>
                <span className="text-sm capitalize text-slate-500">{(cmd.category || "general").replace("_", " ")}</span>
              </div>
            </div>

            <p className="mb-4 text-slate-700 dark:text-slate-200">{cmd.description}</p>

            {cmd.syntax && (
              <div className="mb-4">
                <div className="mb-1 text-sm font-semibold text-slate-600">Syntax</div>
                <code className="block rounded bg-slate-100 p-3 text-sm dark:bg-slate-800">{cmd.syntax}</code>
              </div>
            )}

            {cmd.example && (
              <div>
                <div className="mb-1 text-sm font-semibold text-slate-600">Examples</div>
                <code className="block whitespace-pre-wrap rounded bg-slate-100 p-3 text-sm dark:bg-slate-800">{cmd.example}</code>
              </div>
            )}
          </div>
        ))}
      </div>

      {results.length === 0 && query && !loading && (
        <EmptyState icon=".." title="No commands found" message={`No commands found for \"${query}\"`} />
      )}
    </main>
  );
}
