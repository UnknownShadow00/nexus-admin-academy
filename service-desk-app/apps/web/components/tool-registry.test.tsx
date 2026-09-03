import { TOOL_CATALOG } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import { renderTool } from './tool-registry';

describe('renderTool', () => {
  it('renders every catalog tool through the shared registry', () => {
    for (const tool of TOOL_CATALOG) {
      expect(renderTool(tool.slug)).not.toBeNull();
    }
  });

  it('returns null for an unknown tool', () => {
    expect(renderTool('not-a-tool')).toBeNull();
  });
});
