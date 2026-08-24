import { describe, expect, it } from 'vitest';

import {
  TOOL_CATALOG,
  TOOL_CATEGORIES,
  getToolBySlug,
  getToolsByCategory,
} from './tool-catalog';

describe('tool catalog', () => {
  it('defines ten unique, refresh-safe tool routes', () => {
    const paths = TOOL_CATALOG.map((tool) => tool.path);
    const slugs = TOOL_CATALOG.map((tool) => tool.slug);

    expect(new Set(paths).size).toBe(10);
    expect(new Set(slugs).size).toBe(10);
    expect(paths.every((path) => path.startsWith('/tools/'))).toBe(true);
  });

  it('groups exactly nine menu tools in the documented category order', () => {
    expect(
      TOOL_CATEGORIES.map((category) => ({
        category,
        tools: getToolsByCategory(category).map((tool) => tool.menuLabel),
      })),
    ).toEqual([
      {
        category: 'infrastructure',
        tools: [
          'Directory',
          'Server Room',
          'Remote Desktop',
          'Computer Deployment',
          'PC Shelf',
        ],
      },
      { category: 'knowledge', tools: ['Documentation'] },
      {
        category: 'management',
        tools: ['Device Management', 'Asset Management', 'Ship Manager'],
      },
    ]);
  });

  it('resolves known routes and rejects unknown ones', () => {
    expect(getToolBySlug('remote-desktop')?.path).toBe('/tools/remote-desktop');
    expect(getToolBySlug('device-management')?.path).toBe(
      '/tools/device-management',
    );
    expect(getToolBySlug('not-a-tool')).toBeUndefined();
  });
});
