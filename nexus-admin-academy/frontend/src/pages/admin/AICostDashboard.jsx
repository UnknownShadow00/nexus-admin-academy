import { useEffect, useState } from "react";
import { Activity, DollarSign, TrendingUp, Zap } from "lucide-react";
import { getAIUsageStats } from "../../services/api";
import Spinner from "../../components/Spinner";
import EmptyState from "../../components/EmptyState";

export default function AICostDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const run = async () => {
      try {
        const response = await getAIUsageStats();
        setStats(response.data || null);
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl p-6">
        <Spinner size="lg" text="Loading AI usage stats..." />
      </main>
    );
  }

  if (!stats) {
    return (
      <main className="mx-auto max-w-7xl p-6">
        <EmptyState icon="AI" title="No AI usage yet" message="Generate a quiz or grade a ticket to start seeing costs." />
      </main>
    );
  }

  const summary = stats.summary || { daily_cost: 0, monthly_cost: 0, total_cost: 0 };
  const breakdown = stats.breakdown || [];
  const recentCalls = stats.recent_calls || [];
  const daily = Number(summary.daily_cost || 0);

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">AI Usage and Cost Tracking</h1>
      </header>

      {daily >= 0.8 && daily < 1 && (
        <div className="mb-4 border-l-4 border-yellow-500 bg-yellow-100 p-4 text-slate-900">
          <p className="font-bold">Warning: 80% of daily budget used</p>
          <p className="text-sm">${daily.toFixed(2)} / $1.00 spent today. Budget resets at midnight.</p>
        </div>
      )}

      {daily >= 1 && (
        <div className="mb-4 border-l-4 border-red-500 bg-red-100 p-4 text-slate-900">
          <p className="font-bold">Daily budget limit reached</p>
          <p className="text-sm">All AI features disabled until midnight.</p>
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <DollarSign className="text-green-600" size={18} />
            <span>Daily Cost</span>
          </div>
          <p className="text-2xl font-bold text-green-600">${Number(summary.daily_cost || 0).toFixed(4)}</p>
        </article>

        <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <TrendingUp className="text-blue-600" size={18} />
            <span>Monthly Cost</span>
          </div>
          <p className="text-2xl font-bold text-blue-600">${Number(summary.monthly_cost || 0).toFixed(4)}</p>
        </article>

        <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-2 flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <Zap className="text-amber-500" size={18} />
            <span>Total Cost</span>
          </div>
          <p className="text-2xl font-bold text-amber-500">${Number(summary.total_cost || 0).toFixed(4)}</p>
        </article>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-4 text-xl font-semibold">Breakdown by Feature</h2>
        {breakdown.length === 0 ? (
          <EmptyState icon="--" title="No tracked calls" message="Run AI-powered actions to populate this table." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left dark:border-slate-700">
                  <th className="py-2">Feature</th>
                  <th className="py-2 text-right">Calls</th>
                  <th className="py-2 text-right">Tokens</th>
                  <th className="py-2 text-right">Total Cost</th>
                  <th className="py-2 text-right">Avg / Call</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((row) => (
                  <tr key={row.feature} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 font-medium">{row.feature}</td>
                    <td className="py-2 text-right">{row.calls}</td>
                    <td className="py-2 text-right">{Number(row.tokens || 0).toLocaleString()}</td>
                    <td className="py-2 text-right text-green-600">${Number(row.cost || 0).toFixed(4)}</td>
                    <td className="py-2 text-right">${Number(row.avg_per_call || 0).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
          <Activity size={18} />
          Recent API Calls
        </h2>
        {recentCalls.length === 0 ? (
          <EmptyState icon="--" title="No recent calls" message="Recent AI call history will appear here." />
        ) : (
          <div className="space-y-2">
            {recentCalls.map((call, idx) => (
              <div key={`${call.timestamp || "unknown"}-${idx}`} className="flex items-center justify-between rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
                <div>
                  <p className="font-medium">{call.feature}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {call.model} - {call.timestamp ? new Date(call.timestamp).toLocaleString() : "Unknown time"}
                  </p>
                </div>
                <div className="text-right text-sm">
                  <p>{Number(call.tokens || 0).toLocaleString()} tokens</p>
                  <p className="font-semibold text-green-600">${Number(call.cost || 0).toFixed(4)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
