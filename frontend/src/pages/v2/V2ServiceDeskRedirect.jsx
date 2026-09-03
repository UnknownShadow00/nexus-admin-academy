import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import { launchV2ServiceDesk } from "../../services/api";

export default function V2ServiceDeskRedirect() {
  const { moduleKey, assessmentKey } = useParams();
  const [error, setError] = useState("");
  useEffect(() => {
    launchV2ServiceDesk(moduleKey, assessmentKey, { suppressToast: true })
      .then((res) => { window.location.assign(res.data.launch_url); })
      .catch((err) => setError(err?.userMessage || "The troubleshooting ticket could not be opened."));
  }, [assessmentKey, moduleKey]);
  if (error) return <V2Error title="Ticket unavailable" message={error} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  return <V2Loading text="Opening Service Desk..." />;
}
