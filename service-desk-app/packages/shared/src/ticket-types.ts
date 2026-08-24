import type { Priority, TicketCategory } from './enums';
import type { ToolSlug } from './tool-catalog';

export enum TicketStatus {
  Open = 'open',
  InProgress = 'in-progress',
  Pending = 'pending',
  Resolved = 'resolved',
  Closed = 'closed',
}

export interface RequesterDevice {
  assetTag: string;
  deviceName: string;
  kind: 'desktop' | 'laptop' | 'mobile' | 'peripheral';
  operatingSystem: string;
  state: 'active' | 'attention' | 'offline';
}

export interface Requester {
  contact: string;
  department: string;
  email: string;
  location: string;
  name: string;
}

export interface TicketDescription {
  businessImpact: string;
  issue: string;
  reportedByLine: string;
  troubleshooting: readonly string[];
}

export interface TicketSla {
  dueAt: string;
  target: string;
}

export interface ActivityEvent {
  detail?: string;
  id: string;
  label: string;
  timestamp: string;
  tone?: 'default' | 'info' | 'success' | 'warning';
}

export interface TicketNote {
  body: string;
  createdAt: string;
  id: string;
}

export type SuggestedToolSlug = Extract<
  ToolSlug,
  | 'asset-management'
  | 'company-chat'
  | 'directory'
  | 'device-management'
  | 'documentation'
  | 'computer-deployment'
  | 'remote-desktop'
  | 'server-room'
  | 'shipping-manager'
>;

export interface Ticket {
  activity: readonly ActivityEvent[];
  assignedTo: 'you' | null;
  category: TicketCategory;
  createdAt: string;
  description: TicketDescription;
  device: RequesterDevice;
  escalated: boolean;
  hints: readonly string[];
  /** Persisted reveal progress from the simulation engine's overlay; undefined/0 = fresh ticket. */
  hintsRevealedCount?: number;
  id: `INC${number}`;
  notes: readonly TicketNote[];
  priority: Priority;
  requester: Requester;
  sla: TicketSla;
  status: TicketStatus;
  suggestedTools: readonly SuggestedToolSlug[];
  title: string;
}
