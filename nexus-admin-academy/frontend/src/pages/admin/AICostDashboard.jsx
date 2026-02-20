import { useEffect, useState } from "react";
import { getAIUsageStats } from "../../services/api";

export default function AICostDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getAIUsageStats();
      setData(res.data || null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <main className="mx-auto max-w-6xl p-6">Loading AI usage...</main>;
  if (!data) return <main className="mx-auto max-w-6xl p-6">No data available.</main>;

  const fmt = (n) => `$${Number(n || 0).toFixed(4)}`;

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">AI Cost Dashboard</h1>
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Today", value: fmt(data.summary?.daily_cost) },
          { label: "Last 30 Days", value: fmt(data.summary?.monthly_cost) },
          { label: "All Time", value: fmt(data.summary?.total_cost) },
        ].map((card) => (
          <div key={card.label} className="panel dark:bg-slate-900 dark:border-slate-700 text-center">
            <p className="text-sm text-slate-500">{card.label}</p>
            <p className="text-3xl font-bold mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <h2 className="text-lg font-bold mb-3">By Feature</h2>
        <table className="min-w-full text-sm text-left">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-2 py-2">Feature</th>
              <th className="px-2 py-2">Calls</th>
              <th className="px-2 py-2">Tokens</th>
              <th className="px-2 py-2">Total Cost</th>
              <th className="px-2 py-2">Avg/Call</th>
            </tr>
          </thead>
          <tbody>
            {(data.breakdown || []).map((row) => (
              <tr key={row.feature} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-2 py-2">{row.feature}</td>
                <td className="px-2 py-2">{row.calls}</td>
                <td className="px-2 py-2">{row.tokens?.toLocaleString()}</td>
                <td className="px-2 py-2">{fmt(row.cost)}</td>
                <td className="px-2 py-2">{fmt(row.avg_per_call)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel dark:bg-slate-900 dark:border-slate-700">
        <h2 className="text-lg font-bold mb-3">Recent Calls</h2>
        <table className="min-w-full text-sm text-left">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-2 py-2">Feature</th>
              <th className="px-2 py-2">Model</th>
              <th className="px-2 py-2">Tokens</th>
              <th className="px-2 py-2">Cost</th>
              <th className="px-2 py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {(data.recent_calls || []).map((row, i) => (
              <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-2 py-2">{row.feature}</td>
                <td className="px-2 py-2">{row.model}</td>
                <td className="px-2 py-2">{row.tokens}</td>
                <td className="px-2 py-2">{fmt(row.cost)}</td>
                <td className="px-2 py-2">{row.timestamp ? new Date(row.timestamp).toLocaleString() : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
