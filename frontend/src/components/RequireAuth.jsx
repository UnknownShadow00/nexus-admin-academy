import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { clearAuthSession, getCurrentStudent, getToken, isAuthenticated, wasExplicitlyLoggedOut } from "../hooks/useAuth";
import { authMe } from "../services/api";
import { setSelectedProfile } from "../services/profile";

export default function RequireAuth({ children, passwordChangeOnly = false }) {
  const location = useLocation();
  const [checking, setChecking] = useState(!getToken() && !wasExplicitlyLoggedOut());
  const [authorized, setAuthorized] = useState(!wasExplicitlyLoggedOut() && isAuthenticated());

  useEffect(() => {
    let cancelled = false;

    if (wasExplicitlyLoggedOut()) {
      setAuthorized(false);
      setChecking(false);
      return () => {
        cancelled = true;
      };
    }

    if (getToken()) {
      setAuthorized(isAuthenticated());
      setChecking(false);
      return () => {
        cancelled = true;
      };
    }

    authMe({ suppressToast: true })
      .then((res) => {
        if (cancelled || wasExplicitlyLoggedOut()) return;
        const student = res.data;
        setSelectedProfile({
          id: student.student_id,
          name: student.name,
          email: student.email,
          is_mentor: student.is_mentor,
          must_change_password: student.must_change_password,
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
    return <div className="mx-auto max-w-3xl p-6 text-sm text-slate-500 dark:text-slate-300" role="status">Checking session...</div>;
  }

  if (!authorized) {
    return <Navigate to="/login" replace />;
  }

  const mustChangePassword = Boolean(getCurrentStudent()?.must_change_password);
  if (mustChangePassword && !passwordChangeOnly) {
    return <Navigate to="/change-password" replace state={{ from: location.pathname }} />;
  }
  if (!mustChangePassword && passwordChangeOnly) {
    return <Navigate to="/" replace />;
  }

  return children;
}
