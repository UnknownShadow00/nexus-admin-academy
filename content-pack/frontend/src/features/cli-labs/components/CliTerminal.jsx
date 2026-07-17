import { useEffect, useRef, useState } from "react";

export default function CliTerminal({ prompt, lines, onSubmit, onTabComplete, disabled = false }) {
  const [input, setInput] = useState("");
  const [historyIndex, setHistoryIndex] = useState(-1);
  const scrollRef = useRef(null);
  const historyRef = useRef([]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [lines, prompt]);

  function submit() {
    const command = input;
    if (command.trim()) {
      historyRef.current = [...historyRef.current, command];
      setHistoryIndex(-1);
    }
    setInput("");
    onSubmit(command);
  }

  function handleKeyDown(event) {
    if (disabled) return;
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
      return;
    }
    if (event.key === "Tab") {
      event.preventDefault();
      const completed = onTabComplete?.(input);
      if (completed?.value) setInput(completed.value);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (!historyRef.current.length) return;
      const nextIndex = Math.min(historyIndex + 1, historyRef.current.length - 1);
      setHistoryIndex(nextIndex);
      setInput(historyRef.current[historyRef.current.length - 1 - nextIndex] || "");
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (historyIndex <= 0) {
        setHistoryIndex(-1);
        setInput("");
        return;
      }
      const nextIndex = historyIndex - 1;
      setHistoryIndex(nextIndex);
      setInput(historyRef.current[historyRef.current.length - 1 - nextIndex] || "");
    }
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950 shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2 text-xs font-medium text-slate-400">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
        <span className="ml-2">Cisco IOS</span>
      </div>
      <div
        ref={scrollRef}
        className="h-[34rem] overflow-y-auto whitespace-pre-wrap px-4 py-3 font-mono text-sm leading-6 text-slate-100"
        aria-live="polite"
      >
        {lines.map((line, index) => (
          <div key={`${line}-${index}`} className={line.kind === "input" ? "text-cyan-100" : "text-slate-100"}>
            {line.text || " "}
          </div>
        ))}
        <label className="flex min-h-6 items-center text-cyan-100">
          <span className="shrink-0">{prompt}</span>
          <input
            className="min-w-0 flex-1 bg-transparent pl-1 font-mono text-sm text-cyan-100 caret-cyan-300 outline-none"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            aria-label="CLI command input"
          />
        </label>
      </div>
    </section>
  );
}
