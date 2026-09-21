import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { clearAuthSession, setToken } from "../hooks/useAuth";
import { authChangePassword, authLogout } from "../services/api";
import { setSelectedProfile } from "../services/profile";

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await authChangePassword(
        { new_password: newPassword, confirm_password: confirmPassword },
        { suppressToast: true },
      );
      setToken(response.access_token);
      setSelectedProfile({
        id: response.student_id,
        name: response.name,
        email: response.email,
        is_mentor: response.is_mentor,
        must_change_password: false,
        has_unlocked_capstones: response.has_unlocked_capstones,
        a_plus_progress_pct: response.a_plus_progress_pct,
        a_plus_unlocked: response.a_plus_unlocked,
        a_plus_unlock_threshold_pct: response.a_plus_unlock_threshold_pct,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err?.userMessage || "Password could not be changed. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      await authLogout({ suppressToast: true });
    } finally {
      clearAuthSession();
      navigate("/login", { replace: true });
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">First sign-in</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950 dark:text-white">Choose your password</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
          Replace the temporary password before continuing to Nexus. Use 12 to 72 characters.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm font-medium">New password</span>
            <input
              autoComplete="new-password"
              className="input-field"
              maxLength={72}
              minLength={12}
              onChange={(event) => setNewPassword(event.target.value)}
              required
              type="password"
              value={newPassword}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium">Confirm new password</span>
            <input
              autoComplete="new-password"
              className="input-field"
              maxLength={72}
              minLength={12}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              type="password"
              value={confirmPassword}
            />
          </label>
          {error ? <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200" role="alert">{error}</div> : null}
          <button className="btn-primary w-full" disabled={submitting} type="submit">
            {submitting ? "Changing password..." : "Change password"}
          </button>
          <button className="btn-secondary w-full" onClick={handleLogout} type="button">Sign out</button>
        </form>
      </section>
    </main>
  );
}
