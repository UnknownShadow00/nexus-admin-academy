import { useCallback, useEffect, useState } from "react";

import { getV2Access } from "../services/api";

/**
 * Per-student V2 pilot access, resolved at runtime.
 *
 * The build-time VITE_V2_CURRICULUM_ENABLED flag says whether V2 exists at
 * all; it cannot say whether *this* student is in the pilot. Only the backend
 * knows that, so student-facing V2 navigation asks it.
 *
 * Fails closed: any error, or a request still in flight, means no V2 UI. The
 * server is the real boundary — hiding navigation is a courtesy, not a
 * control — so a wrong guess here is a cosmetic bug, never an exposure.
 */
export function useV2Access(authenticated = true) {
  const [state, setState] = useState({
    masterEnabled: false,
    studentEnabled: false,
    mode: "disabled",
    loading: true,
  });

  const refresh = useCallback(async () => {
    if (!authenticated) {
      setState({ masterEnabled: false, studentEnabled: false, mode: "disabled", loading: false });
      return;
    }
    try {
      const response = await getV2Access({ suppressToast: true });
      const data = response?.data || {};
      setState({
        masterEnabled: Boolean(data.master_enabled),
        studentEnabled: Boolean(data.student_enabled),
        mode: data.mode || "disabled",
        loading: false,
      });
    } catch {
      setState({ masterEnabled: false, studentEnabled: false, mode: "disabled", loading: false });
    }
  }, [authenticated]);

  useEffect(() => {
    let active = true;
    setState((previous) => ({ ...previous, loading: true }));
    refresh().finally(() => {
      if (!active) return;
    });
    return () => {
      active = false;
    };
  }, [refresh]);

  return state;
}
