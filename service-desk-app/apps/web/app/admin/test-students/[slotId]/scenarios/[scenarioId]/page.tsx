import { TestScenarioWorkspace } from '../../../../_components/TestScenarioWorkspace';

export default async function TestScenarioPage({
  params,
}: {
  params: Promise<{ scenarioId: string; slotId: string }>;
}) {
  const { scenarioId, slotId } = await params;
  return <TestScenarioWorkspace scenarioId={scenarioId} slotId={slotId} />;
}
