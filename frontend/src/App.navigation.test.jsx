import { describe, expect, it } from 'vitest';
import { buildStudentNavItems } from './App';

describe('student navigation', () => {
  it('keeps three primary destinations and a contextual course route', () => {
    const items = buildStudentNavItems(true);
    expect(items.slice(0, 3).map((item) => [item.label, item.to])).toEqual([
      ['Today', '/'], ['Service Desk', '/service-desk'], ['Progress', '/progress'],
    ]);
    expect(items.some((item) => item.label === 'Learning V2')).toBe(false);
    expect(items.find((item) => item.label === 'More')?.children).toContainEqual({ to: '/learning-v2', label: 'My Course' });
  });
});
