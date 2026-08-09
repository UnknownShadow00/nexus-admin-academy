import { TicketCategory } from './enums';

export type AchievementThresholdType =
  | 'tickets_resolved'
  | 'hint_free_resolutions'
  | 'fast_resolution_seconds'
  | 'accuracy_percent'
  | 'score_points'
  | `category_resolutions:${TicketCategory}`;

export interface Achievement {
  code: string;
  name: string;
  description: string;
  thresholdType: AchievementThresholdType;
  threshold: number;
}

export const ACHIEVEMENT_DEFINITIONS = [
  {
    code: 'first-ticket',
    name: 'First Ticket',
    description: 'Resolve your first support ticket.',
    thresholdType: 'tickets_resolved',
    threshold: 1,
  },
  {
    code: 'getting-started',
    name: 'Getting Started',
    description: 'Resolve 5 support tickets.',
    thresholdType: 'tickets_resolved',
    threshold: 5,
  },
  {
    code: 'troubleshooter',
    name: 'Troubleshooter',
    description: 'Resolve 10 support tickets.',
    thresholdType: 'tickets_resolved',
    threshold: 10,
  },
  {
    code: 'helpdesk-hero',
    name: 'Helpdesk Hero',
    description: 'Resolve 25 support tickets.',
    thresholdType: 'tickets_resolved',
    threshold: 25,
  },
  {
    code: 'it-veteran',
    name: 'IT Veteran',
    description: 'Resolve 50 support tickets.',
    thresholdType: 'tickets_resolved',
    threshold: 50,
  },
  {
    code: 'self-sufficient',
    name: 'Self-Sufficient',
    description: 'Resolve a ticket without revealing any hints.',
    thresholdType: 'hint_free_resolutions',
    threshold: 1,
  },
  {
    code: 'speed-demon',
    name: 'Speed Demon',
    description: 'Resolve a ticket in under 2 minutes of recorded activity.',
    thresholdType: 'fast_resolution_seconds',
    threshold: 120,
  },
  {
    code: 'sharpshooter',
    name: 'Sharpshooter',
    description: 'Reach at least 90% accuracy on attempted tickets.',
    thresholdType: 'accuracy_percent',
    threshold: 90,
  },
  {
    code: 'score-250',
    name: '250 Club',
    description: 'Earn 250 total practice points.',
    thresholdType: 'score_points',
    threshold: 250,
  },
  {
    code: 'access-specialist',
    name: 'Access Specialist',
    description: 'Resolve 2 access tickets.',
    thresholdType: `category_resolutions:${TicketCategory.Access}`,
    threshold: 2,
  },
  {
    code: 'hardware-specialist',
    name: 'Hardware Specialist',
    description: 'Resolve 2 hardware tickets.',
    thresholdType: `category_resolutions:${TicketCategory.Hardware}`,
    threshold: 2,
  },
  {
    code: 'network-specialist',
    name: 'Network Specialist',
    description: 'Resolve 2 network tickets.',
    thresholdType: `category_resolutions:${TicketCategory.Network}`,
    threshold: 2,
  },
  {
    code: 'software-specialist',
    name: 'Software Specialist',
    description: 'Resolve 2 software tickets.',
    thresholdType: `category_resolutions:${TicketCategory.Software}`,
    threshold: 2,
  },
] as const satisfies readonly Achievement[];
