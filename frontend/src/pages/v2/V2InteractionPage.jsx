import { Link, useParams } from "react-router-dom";
import V2Interaction from "../../components/v2/V2Interaction";

export default function V2InteractionPage() {
  const { moduleKey, interactionKey } = useParams();
  return <main className="mx-auto max-w-4xl space-y-6 p-4 pb-20 sm:p-6">
    <Link className="text-sm font-semibold text-blue-700 hover:underline dark:text-blue-300" to={`/learning-v2/modules/${moduleKey}`}>← Back to module</Link>
    <V2Interaction moduleKey={moduleKey} interactionKey={interactionKey} />
  </main>;
}
