import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { clearToken, isAuthenticated, setToken } from "../hooks/useAuth";
import { authLogin } from "../services/api";
import { clearSelectedProfile, setSelectedProfile } from "../services/profile";

const initialLoginForm = { username: "", password: "" };

function getErrorMessage(error) {
  if (typeof error?.userMessage === "string") return error.userMessage;
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (typeof error?.response?.data?.error === "string") return error.response.data.error;
  return "Request failed";
}

// Only same-origin relative paths are honored. Protocol-relative URLs and
// backslash-based browser path confusion can redirect off-site, so reject both.
function safeNextPath(rawNext) {
  return typeof rawNext === "string" && rawNext.startsWith("/") && !rawNext.startsWith("//") && !rawNext.includes("\\")
    ? rawNext
    : "/";
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = safeNextPath(searchParams.get("next"));
  const [loginForm, setLoginForm] = useState(initialLoginForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated()) {
    return <Navigate to={nextPath} replace />;
  }

  async function handleSuccess(response) {
    clearToken();
    clearSelectedProfile();
    setToken(response.access_token);
    setSelectedProfile({
      id: response.student_id,
      name: response.name,
      email: response.email,
      is_mentor: response.is_mentor,
      has_unlocked_capstones: response.has_unlocked_capstones,
      a_plus_progress_pct: response.a_plus_progress_pct,
      a_plus_unlocked: response.a_plus_unlocked,
      a_plus_unlock_threshold_pct: response.a_plus_unlock_threshold_pct,
    });
    if (nextPath === "/service-desk" || nextPath.startsWith("/service-desk/")) {
      window.location.assign(nextPath);
      return;
    }
    navigate(nextPath);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await authLogin(loginForm, { suppressToast: true });
      await handleSuccess(response);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 px-6 py-10 text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-950/90 p-8 shadow-2xl shadow-black/30">
        <h1 className="text-center text-3xl font-semibold text-white">Nexus Admin Academy</h1>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm text-slate-300">Username</span>
            <input
              className="input-field border-slate-700 bg-slate-950"
              value={loginForm.username}
              onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))}
              required
              type="text"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm text-slate-300">Password</span>
            <input
              className="input-field border-slate-700 bg-slate-950"
              value={loginForm.password}
              onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))}
              required
              type="password"
            />
          </label>

          {error ? (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <button className="btn-primary w-full" disabled={submitting} type="submit">
            {submitting ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-800 pt-6">
          <Link
            className="btn-secondary flex w-full items-center justify-center border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800"
            to="/admin-login"
          >
            Admin Login
          </Link>
        </div>
      </section>
    </main>
  );
}
