import { DashboardStats } from './DashboardStats';
import { TicketQueue } from './TicketQueue';

export function DashboardContent() {
  return (
    <div className="space-y-5 md:space-y-6">
      <DashboardStats />
      <TicketQueue />
    </div>
  );
}
