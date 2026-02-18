import { useEffect, useState } from "react";
import { Award, CheckCircle, Circle } from "lucide-react";
import { getPromotionStatus } from "../services/api";
import { getSelectedProfile } from "../services/profile";

function RequirementCard({ requirement }) {
  return (
    <div className="mb-2 rounded border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <Circle className="mt-1 text-amber-600" size={18} />
        <div className="flex-1">
          <div className="mb-2 font-medium">{requirement.description}</div>
          {requirement.progress ? (
            <div className="space-y-1 text-sm">
              {Object.entries(requirement.progress).map(([key, data]) => (
                <div key={key} className="flex justify-between">
                  <span>{key}</span>
                  <span>
                    {data.current}/{data.required}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function PromotionTracker() {
  const studentId = getSelectedProfile()?.id || 1;
  const [currentRole, setCurrentRole] = useState(null);
  const [nextRole, setNextRole] = useState(null);
  const [eligibility, setEligibility] = useState(null);

  useEffect(() => {
    const run = async () => {
      const res = await getPromotionStatus(studentId);
      setCurrentRole(res.current_role || null);
      setNextRole(res.next_role || null);
      setEligibility(res.eligibility || null);
    };
    run();
  }, [studentId]);

  if (!currentRole) return <main className="mx-auto max-w-4xl p-6">Loading promotion status...</main>;

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-3xl font-bold">Career Progression</h1>
      <div className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white">
        <div className="flex items-center gap-3">
          <Award size={30} />
          <div>
            <div className="text-sm text-blue-100">Current Role</div>
            <div className="text-2xl font-bold">{currentRole.name}</div>
          </div>
        </div>
      </div>

      {nextRole && eligibility ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-500">Next Role</div>
              <div className="text-2xl font-bold">{nextRole.name}</div>
            </div>
            <div className="text-4xl font-bold text-blue-600">{eligibility.completion_percent}%</div>
          </div>
          <div className="mb-6 h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700">
            <div className="h-4 rounded-full bg-blue-600" style={{ width: `${eligibility.completion_percent}%` }} />
          </div>
          {eligibility.eligible ? (
            <div className="rounded border border-green-200 bg-green-50 p-4 text-green-900">
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle size={18} />
                Eligible for promotion
              </div>
            </div>
          ) : (
            <div>
              <h3 className="mb-3 font-semibold">Still Needed</h3>
              {(eligibility.requirements_missing || []).map((req, idx) => (
                <RequirementCard key={idx} requirement={req} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </main>
  );
}

