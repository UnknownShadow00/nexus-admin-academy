import { useEffect, useMemo, useState } from "react";
import TerminalWidget from "../components/Terminal";
import { searchCommands } from "../services/api";

export default function TerminalCommandsPage() {
  const [query, setQuery] = useState("");
  const [commands, setCommands] = useState([]);
  const [selectedCommand, setSelectedCommand] = useState("");
  const [sessionText, setSessionText] = useState("");

  useEffect(() => {
    const timer = setTimeout(async () => {
      const res = await searchCommands(query);
      setCommands(res.commands || []);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const grouped = useMemo(() => {
    const map = new Map();
    for (const command of commands) {
      const category = command.category || "general";
      if (!map.has(category)) map.set(category, []);
      map.get(category).push(command);
    }
    return Array.from(map.entries());
  }, [commands]);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <h1 className="mb-4 text-2xl font-bold">Terminal & Commands</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel dark:border-slate-700 dark:bg-slate-900">
          <input
            className="input-field mb-3"
            placeholder="Search command name or category..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="max-h-[560px] space-y-3 overflow-auto pr-1">
            {grouped.map(([category, rows]) => (
              <div key={category}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{category}</p>
                <div className="space-y-2">
                  {rows.map((cmd) => (
                    <button
                      key={cmd.id}
                      className="w-full rounded border border-slate-200 p-3 text-left hover:border-blue-300 hover:bg-blue-50 dark:border-slate-700 dark:hover:bg-slate-800"
                      onClick={() => setSelectedCommand(cmd.command)}
                    >
                      <p className="font-mono font-semibold text-blue-700 dark:text-blue-300">
                        {cmd.command} {cmd.syntax ? ` ${cmd.syntax}` : ""}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-300">{cmd.description}</p>
                      {cmd.example ? <p className="mt-1 text-xs text-slate-500">Example: {cmd.example}</p> : null}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <TerminalWidget prefillCommand={selectedCommand} onSessionChange={setSessionText} />
          <button
            className="btn-secondary w-full"
            onClick={async () => {
              await navigator.clipboard.writeText(sessionText || "");
              localStorage.setItem("terminal_session_history", sessionText || "");
            }}
          >
            Copy session to clipboard
          </button>
        </section>
      </div>
    </main>
  );
}

