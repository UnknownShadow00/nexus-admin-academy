import { TestStudentDashboard } from '../../_components/TestStudentDashboard';

export default async function TestStudentPage({
  params,
}: {
  params: Promise<{ slotId: string }>;
}) {
  const { slotId } = await params;
  return <TestStudentDashboard slotId={slotId} />;
}
