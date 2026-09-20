import { describe, expect, it } from 'vitest';
import { buildContinueTarget } from './StudentHome';

describe('Today V2 next step', () => {
  it('prefers the backend V2 Continue target over the legacy path', () => {
    const target = buildContinueTarget({ current: {
      certification: { name: 'CompTIA A+' }, module: { title: 'Networking' },
      continue: { kind: 'quick_check', title: 'Ports check', route: '/learning-v2/modules/network/assessments/ports', status: 'in_progress' },
      progress: { lessons: { completed: 1 }, assessments: {} },
    } }, { current_module: { title: 'Legacy orientation', route: '/learning-path' } });
    expect(target).toMatchObject({ activityType: 'Quick Check', label: 'Continue', title: 'Ports check', to: '/learning-v2/modules/network/assessments/ports', v2: true });
  });

  it('uses the activity status and available duration for beginner action wording', () => {
    const target = buildContinueTarget({ current: {
      certification: { name: 'CompTIA A+' }, module: { title: 'Networking' },
      continue: { kind: 'lesson', title: 'IP basics', route: '/learning-v2/modules/network/lessons/ip', status: 'not_started', estimated_minutes: 12 },
      progress: { lessons: { completed: 4 } },
    } });
    expect(target).toMatchObject({ label: 'Start', status: 'not_started', estimatedMinutes: 12 });
  });
});
