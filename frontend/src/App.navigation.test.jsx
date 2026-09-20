import { describe, expect, it } from 'vitest';
import { buildStudentNavItems } from './App';

describe('student navigation', () => {
  it('keeps beginner destinations primary and legacy routes secondary', () => {
    const items = buildStudentNavItems(true);
    expect(items.slice(0, 4).map((item) => [item.label, item.to])).toEqual([
      ['Today', '/'], ['Service Desk', '/service-desk'], ['Progress', '/progress'], ['My Course', '/learning-v2'],
    ]);
    expect(items.some((item) => item.label === 'Learning V2')).toBe(false);
    expect(items.find((item) => item.label === 'Extra Practice')?.children).toContainEqual({ to: '/learning-path', label: 'Legacy Learning Path' });
  });
});
