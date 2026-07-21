import { Link } from "react-router-dom";
import Banner from "./ui/Banner";

export function getPrerequisiteLock(error) {
  const body = error?.response?.data;
  const payload = body?.code === "PREREQUISITE_NOT_MET" ? body : body?.detail;
  return payload?.code === "PREREQUISITE_NOT_MET" ? payload : null;
}

export default function PrerequisiteLock({ lock }) {
  if (!lock) return null;

  return (
    <Banner variant="warning">
      <span>
        {lock.error}{" "}
        {lock.data?.next_action_route ? (
          <Link className="underline" to={lock.data.next_action_route}>
            Continue your current week
          </Link>
        ) : null}
      </span>
    </Banner>
  );
}
