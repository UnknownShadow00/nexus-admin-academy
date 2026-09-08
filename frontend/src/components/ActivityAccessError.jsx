import { Link, useLocation } from "react-router-dom";
import { activityOrigin, withActivityOrigin } from "../utils/activityOrigin";
export default function ActivityAccessError({ error, kind, onRetry }) {
  const origin = activityOrigin(useLocation());
  const body = error?.response?.data;
  const prerequisite = body?.code === "PREREQUISITE_NOT_MET";
  const unavailable = error?.response?.status === 404;
  const data = body?.data || {};
  return (
    <section className="panel" role="alert">
      <h1 className="text-xl font-bold">
        {prerequisite
          ? `${kind} locked`
          : unavailable
            ? `${kind} unavailable`
            : `Unable to load ${kind.toLowerCase()}`}
      </h1>
      <p className="mt-2">
        {prerequisite
          ? body.error
          : unavailable
            ? "This activity is unavailable. Return to My Course to find your next activity."
            : "The activity could not be loaded. Please try again."}
      </p>
      {prerequisite ? (
        <Link
          className="btn-primary mt-4"
          to={withActivityOrigin(
            data.next_action_route || "/learning-path",
            origin?.route,
            origin?.label,
          )}
        >
          Go to{" "}
          {data.missing_prerequisite ||
            data.current_module_title ||
            "required work"}
        </Link>
      ) : (
        <>
          {onRetry ? (
            <button
              className="btn-primary mt-4"
              onClick={onRetry}
              type="button"
            >
              Try again
            </button>
          ) : null}
          <Link className="btn-secondary mt-4" to="/learning-path">
            My Course
          </Link>
        </>
      )}
    </section>
  );
}
