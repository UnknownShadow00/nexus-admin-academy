import { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { getCurrentStudent, setToken } from "../hooks/useAuth";
import { adminSessionLogout, adminSessionStatus, getStudentTokenAsAdmin } from "../services/api";
import { setSelectedProfile } from "../services/profile";

export default function AdminAccessGate({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  const adminLoginPath = useMemo(() => {
    const redirectTo = `${location.pathname}${location.search}${location.hash}`;
    return `/admin-login?redirect=${encodeURIComponent(redirectTo)}`;
  }, [location.hash, location.pathname, location.search]);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await adminSessionStatus({ suppressToast: true });
        setAuthenticated(Boolean(res.data?.authenticated));
      } catch {
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  const onLogout = async () => {
    await adminSessionLogout();
    setAuthenticated(false);
  };

  const onSwitchToStudent = async () => {
    try {
      const res = await getStudentTokenAsAdmin();
      if (res?.data?.access_token) {
        setToken(res.data.access_token);
        setSelectedProfile({
          id: res.data.student_id,
          name: res.data.name,
          email: res.data.email,
          is_mentor: res.data.is_mentor,
        });
        navigate("/", { replace: true });
      }
    } catch {
      // Fallback: just redirect to login
      navigate("/login", { replace: true });
    }
  };

  if (loading) {
    return <main className="mx-auto max-w-3xl p-6">Checking admin session and waking the backend if needed...</main>;
  }

  if (!loading && !authenticated) {
    const mentor = getCurrentStudent();
    if (mentor?.is_mentor) {
      return (
        <>
          <div className="mx-auto mt-2 max-w-7xl px-6">
            <div className="rounded border border-blue-300 bg-blue-50 px-4 py-2 text-sm text-blue-800 dark:border-blue-700 dark:bg-blue-950/30 dark:text-blue-200">
              Mentor view (read-only)
            </div>
          </div>
          {children}
        </>
      );
    }
  }

  if (!authenticated) {
    return <Navigate to={adminLoginPath} replace />;
  }

  return (
    <>
      <div className="mx-auto mt-2 flex max-w-7xl justify-end gap-2 px-6">
        <button className="btn-secondary text-xs" type="button" onClick={onSwitchToStudent}>
          Switch to Student View
        </button>
        <button className="btn-secondary text-xs" type="button" onClick={onLogout}>
          Admin Sign Out
        </button>
      </div>
      {children}
    </>
  );
}
