import { Cable, Monitor, Network } from "lucide-react";

function DeviceIcon({ type }) {
  if (type === "pc") return <Monitor size={16} />;
  return <Network size={16} />;
}

export default function TopologyPanel({ topology }) {
  const devices = topology?.devices || [];
  const interfaces = topology?.interfaces || {};

  return (
    <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Topology</h2>
      <div className="space-y-2">
        {devices.map((device) => (
          <div key={device.id} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-950">
            <span className="flex items-center gap-2 font-medium text-slate-700 dark:text-slate-200">
              <DeviceIcon type={device.type} />
              {device.label}
            </span>
            {device.connectedTo ? (
              <span className="text-xs text-slate-500 dark:text-slate-400">{device.connectedTo} | VLAN {device.vlan}</span>
            ) : null}
          </div>
        ))}
      </div>
      {Object.keys(interfaces).length ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <Cable size={14} />
            Interfaces
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(interfaces).map(([name, details]) => (
              <div key={name} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950">
                <div className="font-semibold text-slate-700 dark:text-slate-200">{name}</div>
                <div className="text-slate-500 dark:text-slate-400">{details.shutdown ? "shutdown" : details.status || "up"}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
