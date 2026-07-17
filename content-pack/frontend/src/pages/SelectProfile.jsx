import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStudents } from "../services/api";
import { setSelectedProfile } from "../services/profile";

const fallbackProfiles = [
  { id: 1, name: "Alex" },
  { id: 2, name: "Jordan" },
  { id: 3, name: "Sam" },
  { id: 4, name: "Taylor" },
  { id: 5, name: "Riley" },
];

export default function SelectProfile() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState(fallbackProfiles);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await getStudents();
        const rows = (res.data || []).map((s) => ({ id: s.id, name: s.name }));
        if (rows.length) setProfiles(rows);
      } catch {
        // Fallback list remains.
      }
    };
    run();
  }, []);

  return (
    <main className="mx-auto max-w-4xl p-6">
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Select Profile</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Choose your student profile to continue.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              className="rounded-lg border border-slate-200 bg-white p-4 text-left hover:border-blue-300 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              onClick={() => {
                setSelectedProfile(profile);
                navigate("/");
              }}
            >
              <p className="text-lg font-semibold">{profile.name}</p>
              <p className="text-xs text-slate-500">Student #{profile.id}</p>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

