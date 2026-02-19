import { useEffect, useState } from "react";
import { adminSessionLogin, adminSessionLogout, adminSessionStatus } from "../services/api";

export default function AdminAccessGate({ children }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [adminKey, setAdminKey] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await adminSessionStatus();
        setAuthenticated(Boolean(res.data?.authenticated));
      } catch {
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  const onLogin = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await adminSessionLogin(adminKey);
      setAuthenticated(true);
      setAdminKey("");
    } finally {
      setSubmitting(false);
    }
  };

  const onLogout = async () => {
    await adminSessionLogout();
    setAuthenticated(false);
  };

  if (loading) {
    return <main className="mx-auto max-w-3xl p-6">Checking admin session...</main>;
  }

  if (!authenticated) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <section className="panel dark:border-slate-700 dark:bg-slate-900">
          <h1 className="text-2xl font-bold">Admin Login</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Enter admin key to access admin tools.</p>
          <form className="mt-4 flex gap-2" onSubmit={onLogin}>
            <input
              className="input-field flex-1"
              type="password"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="Admin key"
            />
            <button className="btn-primary" type="submit" disabled={submitting || !adminKey.trim()}>
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <>
      <div className="mx-auto mt-2 flex max-w-7xl justify-end px-6">
        <button className="btn-secondary text-xs" type="button" onClick={onLogout}>
          Admin Sign Out
        </button>
      </div>
      {children}
    </>
  );
}

