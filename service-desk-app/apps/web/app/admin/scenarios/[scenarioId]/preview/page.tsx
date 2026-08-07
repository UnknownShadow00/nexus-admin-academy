import { ScenarioPreview } from '../../../_components/ScenarioPreview';

export default async function ScenarioPreviewPage({
  params,
}: {
  params: Promise<{ scenarioId: string }>;
}) {
  const { scenarioId } = await params;
  return <ScenarioPreview scenarioId={scenarioId} />;
}
