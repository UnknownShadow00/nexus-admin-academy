import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { clearAuthSession, getToken, isAuthenticated } from "../hooks/useAuth";
import { authMe } from "../services/api";
import { setSelectedProfile } from "../services/profile";

export default function RequireAuth({ children }) {
  const [checking, setChecking] = useState(!getToken());
  const [authorized, setAuthorized] = useState(isAuthenticated());

  useEffect(() => {
    let cancelled = false;

    if (getToken()) {
      setAuthorized(isAuthenticated());
      setChecking(false);
      return () => {
        cancelled = true;
      };
    }

    authMe({ suppressToast: true })
      .then((res) => {
        if (cancelled) return;
        const student = res.data;
        setSelectedProfile({
          id: student.student_id,
          name: student.name,
          email: student.email,
          is_mentor: student.is_mentor,
          has_unlocked_capstones: student.has_unlocked_capstones,
          a_plus_progress_pct: student.a_plus_progress_pct,
          a_plus_unlocked: student.a_plus_unlocked,
          a_plus_unlock_threshold_pct: student.a_plus_unlock_threshold_pct,
        });
        setAuthorized(true);
      })
      .catch(() => {
        if (cancelled) return;
        clearAuthSession();
        setAuthorized(false);
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (checking) {
    return <main className="mx-auto max-w-3xl p-6 text-sm text-slate-500 dark:text-slate-300">Checking session...</main>;
  }

  if (!authorized) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
