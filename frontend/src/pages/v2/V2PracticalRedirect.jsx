import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import { getV2Module } from "../../services/api";

export default function V2PracticalRedirect() {
  const { moduleKey, assessmentKey } = useParams();
  const [target, setTarget] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { getV2Module(moduleKey, { suppressToast: true }).then((res) => { const item = res.data.assessments.find((assessment) => assessment.key === assessmentKey && assessment.role === "practical"); if (!item?.lab_id) setError(item?.unavailable?.reason || "This practical has not been prepared for students yet. Choose another available activity in the module."); else setTarget(`/labs/${item.lab_id}?v2Module=${encodeURIComponent(moduleKey)}&v2Assessment=${encodeURIComponent(assessmentKey)}`); }).catch((err) => setError(err?.userMessage || "The practical could not be loaded.")); }, [assessmentKey, moduleKey]);
  if (error) return <V2Error title="Practical unavailable" message={error} moduleRoute={`/learning-v2/modules/${moduleKey}`} />;
  if (!target) return <V2Loading text="Opening practical..." />;
  return <Navigate replace to={target} />;
}
