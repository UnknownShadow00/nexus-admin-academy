import { useEffect, useMemo, useState } from "react";
import { getSquadDashboard } from "../services/api";
import { getSelectedProfile } from "../services/profile";

export default function SquadDashboard() {
  const selected = getSelectedProfile();
  const [data, setData] = useState(null);
  const [selectedStudentId, setSelectedStudentId] = useState(selected?.id || 1);

  useEffect(() => {
    const run = async () => {
      const res = await getSquadDashboard(selectedStudentId);
      setData(res.data || null);
    };
    run();
  }, [selectedStudentId]);

  const members = data?.members || [];
  const feed = data?.activity_feed || [];
  const leads = data?.weekly_domain_leads || [];
  const mastery = data?.selected_student_mastery || [];
  const selectedMember = useMemo(
    () => members.find((m) => m.student_id === selectedStudentId),
    [members, selectedStudentId]
  );

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold">Squad Accountability Hub</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Activity feed, active status, domain leads, and teammate mastery.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="panel lg:col-span-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-semibold">Live Activity Feed</h2>
          <div className="space-y-2">
            {feed.map((item) => (
              <div key={item.id} className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{item.student_name} - {item.title}</p>
                  <p className="text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString() : ""}</p>
                </div>
                <p className="mt-1 text-slate-600 dark:text-slate-300">{item.detail || item.activity_type}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-semibold">Domain Leads</h2>
          <div className="space-y-2">
            {leads.map((lead) => (
              <div key={`${lead.domain_id}-${lead.student_id}`} className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
                <p className="font-semibold">{lead.badge_name}</p>
                <p>{lead.student_name}</p>
                <p className="text-xs text-slate-500">Domain {lead.domain_id}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-semibold">Squad Status</h2>
          <div className="space-y-2">
            {members.map((member) => (
              <button
                key={member.student_id}
                className={`w-full rounded border p-3 text-left text-sm ${member.student_id === selectedStudentId ? "border-blue-400 bg-blue-50 dark:bg-slate-800" : "border-slate-200 dark:border-slate-700"}`}
                onClick={() => setSelectedStudentId(member.student_id)}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium">{member.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${member.status === "Active" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {member.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{member.total_xp} XP</p>
              </button>
            ))}
          </div>
        </div>

        <div className="panel dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-lg font-semibold">Teammate Mastery</h2>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            {selectedMember ? `${selectedMember.name}'s domain mastery` : "Select a teammate"}
          </p>
          <div className="space-y-3">
            {mastery.map((row) => (
              <div key={row.domain_id}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{row.domain_name}</span>
                  <span>{row.mastery_percent}%</span>
                </div>
                <div className="h-3 rounded-full bg-slate-200 dark:bg-slate-700">
                  <div className="h-3 rounded-full bg-blue-600" style={{ width: `${row.mastery_percent}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

