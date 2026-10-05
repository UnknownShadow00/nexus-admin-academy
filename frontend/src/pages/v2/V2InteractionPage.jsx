import { Link, useParams } from "react-router-dom";
import V2Interaction from "../../components/v2/V2Interaction";
import PageContainer from "../../components/ui/PageContainer";

export default function V2InteractionPage() {
  const { moduleKey, interactionKey } = useParams();
  return <PageContainer width="reading" className="space-y-6">
    <nav aria-label="Breadcrumb" className="text-sm"><Link to="/learning-v2">My Course</Link><span aria-hidden="true"> / </span><Link to={`/learning-v2/modules/${moduleKey}`}>Stage</Link><span aria-hidden="true"> / </span><span aria-current="page">Interaction</span></nav>
    <V2Interaction moduleKey={moduleKey} interactionKey={interactionKey} />
  </PageContainer>;
}
