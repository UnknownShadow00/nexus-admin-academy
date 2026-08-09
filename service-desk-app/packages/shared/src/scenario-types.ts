import type { Priority, TicketCategory } from './enums';
import type {
  Requester,
  RequesterDevice,
  TicketDescription,
  TicketSla,
} from './ticket-types';
import type { AssetStatus } from './enums';

export interface DirectoryUserOverlaySeed {
  disabled: boolean;
  groupChanges: {
    added: string[];
    removed: string[];
  };
  locked: boolean;
  mfaEnrolled: boolean;
}

export interface AssetOverlaySeed {
  assignedDirectoryUserId: string | null;
  status: AssetStatus;
}

export interface ChatMessageSeed {
  body: string;
  contactId: string;
  fromStudent?: boolean;
  triggerKey?: string | null;
}

export interface ScenarioInitialWorldState {
  directoryOverlaySeeds: Record<string, Partial<DirectoryUserOverlaySeed>>;
  assetOverlaySeeds: Record<string, Partial<AssetOverlaySeed>>;
  chatMessageSeeds: ChatMessageSeed[];
}

export interface ScenarioTemplate {
  activeVersionId: string | null;
  category: TicketCategory;
  createdAt: string;
  id: string;
  priority: Priority;
  slug: string;
  title: string;
}

export interface ScenarioActionRule {
  /**
   * Must be an ActionEvent.type emitted by simulation-engine. Valid examples:
   * "ticket.close", "directory.update_groups", "directory.unlock_account",
   * "asset.change_status", and "chat.send_message".
   */
  actionType: string;
  description: string;
  id: string;
  payloadMatch?: Record<string, unknown>;
}

export type ScenarioPredicateType =
  | 'action_event_occurred'
  | 'directory_group_membership'
  | 'directory_user_field'
  | 'ticket_verified_resolved';

export interface ScenarioObjective {
  description: string;
  id: string;
  order: number;
  pointValue: number;
  predicateParams: Record<string, unknown>;
  predicateType: ScenarioPredicateType;
  required: boolean;
}

export interface ScenarioHint {
  id: string;
  order: number;
  pointPenalty: number;
  text: string;
}

export interface ScenarioVersion {
  definitionHash?: string;
  description: TicketDescription;
  device: RequesterDevice;
  difficulty: 'easy' | 'medium' | 'hard';
  explanation: string;
  forbiddenActions: ScenarioActionRule[];
  hints: ScenarioHint[];
  id: string;
  initialWorldState: ScenarioInitialWorldState;
  objectives: ScenarioObjective[];
  pointValue: number;
  publishedAt: string | null;
  requester: Requester;
  requiredActions: ScenarioActionRule[];
  scenarioId: string;
  sla: TicketSla;
  version: number;
}

export interface ScenarioRecord {
  template: ScenarioTemplate;
  versions: ScenarioVersion[];
}

export type ScenarioVersionDraftData = Omit<
  ScenarioVersion,
  'definitionHash' | 'id' | 'publishedAt' | 'scenarioId' | 'version'
> &
  Pick<ScenarioTemplate, 'category' | 'priority' | 'slug' | 'title'>;
