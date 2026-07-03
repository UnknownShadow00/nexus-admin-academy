import { useState } from "react";

export default function PcTerminal({ lines, onSubmit, disabled = false, devices = [] }) {
  const [input, setInput] = useState("");
  const [activePcId, setActivePcId] = useState(devices[0]?.id || "PC-A");
  const pcOptions = devices.length ? devices : [{ id: "PC-A", label: "PC-A" }];
  const activePc = pcOptions.find((device) => device.id === activePcId) || pcOptions[0];

  function submit() {
    const command = input;
    setInput("");
    onSubmit(command, activePc.id);
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-300 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 dark:border-slate-800 dark:text-slate-300">
        <span>{activePc.label || activePc.id} Terminal</span>
        {pcOptions.length > 1 ? (
          <select
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-950"
            value={activePc.id}
            onChange={(event) => setActivePcId(event.target.value)}
            disabled={disabled}
            aria-label="Select PC terminal"
          >
            {pcOptions.map((device) => (
              <option key={device.id} value={device.id}>
                {device.label || device.id}
              </option>
            ))}
          </select>
        ) : null}
      </div>
      <div className="max-h-48 overflow-y-auto whitespace-pre-wrap px-4 py-3 font-mono text-sm text-slate-800 dark:text-slate-100">
        {lines.map((line, index) => (
          <div key={`${line}-${index}`}>{line || " "}</div>
        ))}
        <label className="flex min-h-6 items-center">
          <span className="shrink-0">{activePc.id}&gt; </span>
          <input
            className="min-w-0 flex-1 bg-transparent pl-1 font-mono text-sm outline-none"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                submit();
              }
            }}
            disabled={disabled}
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            aria-label="PC terminal command input"
          />
        </label>
      </div>
    </section>
  );
}
