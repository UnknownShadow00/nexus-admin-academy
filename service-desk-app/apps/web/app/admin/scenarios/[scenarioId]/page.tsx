import { ScenarioBuilder } from '../../_components/ScenarioBuilder';

export default async function ScenarioPage({
  params,
}: {
  params: Promise<{ scenarioId: string }>;
}) {
  const { scenarioId } = await params;
  return <ScenarioBuilder existingScenarioId={scenarioId} />;
}
