import { describe, expect, it } from 'vitest';

import {
  TOOL_CATALOG,
  TOOL_CATEGORIES,
  getToolBySlug,
  getToolsByCategory,
} from './tool-catalog';

describe('tool catalog', () => {
  it('defines nine unique, refresh-safe tool routes', () => {
    const paths = TOOL_CATALOG.map((tool) => tool.path);
    const slugs = TOOL_CATALOG.map((tool) => tool.slug);

    expect(new Set(paths).size).toBe(9);
    expect(new Set(slugs).size).toBe(9);
    expect(paths.every((path) => path.startsWith('/tools/'))).toBe(true);
  });

  it('groups exactly eight menu tools in the documented category order', () => {
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
        tools: ['Asset Management', 'Ship Manager'],
      },
    ]);
  });

  it('resolves known routes and rejects unknown ones', () => {
    expect(getToolBySlug('remote-desktop')?.path).toBe('/tools/remote-desktop');
    expect(getToolBySlug('not-a-tool')).toBeUndefined();
  });
});
