import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { adminSessionLogin, adminSessionStatus } from "../services/api";

const initialForm = { username: "", password: "" };
const defaultRedirectTarget = "/admin";

function getErrorMessage(error) {
  if (typeof error?.userMessage === "string") return error.userMessage;
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (typeof error?.response?.data?.error === "string") return error.response.data.error;
  return "Request failed";
}

function resolveRedirectTarget(search) {
  const redirect = new URLSearchParams(search).get("redirect") || defaultRedirectTarget;
  return redirect.startsWith("/admin") ? redirect : defaultRedirectTarget;
}

export default function AdminLoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const redirectTo = useMemo(() => resolveRedirectTarget(location.search), [location.search]);
  const [form, setForm] = useState(initialForm);
  const [checkingSession, setCheckingSession] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        const res = await adminSessionStatus({ suppressToast: true });
        if (active && res.data?.authenticated) {
          navigate(redirectTo, { replace: true });
          return;
        }
      } catch {
        // Keep the user on the login page if the status check fails.
      } finally {
        if (active) {
          setCheckingSession(false);
        }
      }
    };

    run();
    return () => {
      active = false;
    };
  }, [navigate, redirectTo]);

  async function handleSubmit(event) {
    event.preventDefault();

    const username = form.username.trim();
    const password = form.password.trim();

    if (!username || !password) {
      setError("Username and password are required");
      return;
    }

    setError("");
    setSubmitting(true);

    try {
      await adminSessionLogin({ username, password }, { suppressToast: true });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 items-center justify-center px-6 py-10">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/70 dark:border-slate-800 dark:bg-slate-900 dark:shadow-black/30">
        <div className="space-y-2">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-600 dark:text-blue-300">Admin Access</p>
          <h1 className="text-3xl font-semibold text-slate-900 dark:text-slate-100">Admin Login</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Sign in with your admin username and password to continue to admin tools.
          </p>
        </div>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm text-slate-600 dark:text-slate-300">Username</span>
            <input
              autoComplete="username"
              className="input-field"
              onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
              required
              type="text"
              value={form.username}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm text-slate-600 dark:text-slate-300">Password</span>
            <input
              autoComplete="current-password"
              className="input-field"
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              required
              type="password"
              value={form.password}
            />
          </label>

          {error ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200">
              {error}
            </div>
          ) : null}

          <button className="btn-primary w-full" disabled={checkingSession || submitting} type="submit">
            {checkingSession ? "Checking session..." : submitting ? "Logging in..." : "Login"}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-500 dark:text-slate-400">
          First admin request can take up to 30 seconds while Render wakes the backend.
        </p>

        <div className="mt-6 flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
          <span>Student login stays at `/login`.</span>
          <Link className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-300 dark:hover:text-blue-200" to="/login">
            Back to student login
          </Link>
        </div>
      </section>
    </main>
  );
}
