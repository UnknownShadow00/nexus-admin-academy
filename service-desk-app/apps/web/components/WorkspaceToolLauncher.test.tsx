import { TOOL_CATALOG, TicketCategory } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { WorkspaceToolLauncher } from './WorkspaceToolLauncher';

describe('WorkspaceToolLauncher', () => {
  it('puts guided suggestions before the full ten-tool catalog', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceToolLauncher
        activeToolSlug={null}
        experienceMode="guided"
        onSelectTool={vi.fn()}
        ticketCategory={TicketCategory.Network}
        ticketId="INC2510"
        toolSlugs={['remote-desktop', 'documentation']}
      />,
    );

    expect(markup.indexOf('Recommended places to start')).toBeLessThan(
      markup.indexOf('All tools'),
    );
    for (const tool of TOOL_CATALOG) {
      expect(markup).toContain(tool.menuLabel);
    }
  });

  it('shows only the full catalog in assessment mode', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceToolLauncher
        activeToolSlug="directory"
        experienceMode="assessment"
        onSelectTool={vi.fn()}
        ticketCategory={TicketCategory.Access}
        ticketId="INC2511"
        toolSlugs={['directory']}
      />,
    );

    expect(markup).toContain('Technician tools');
    expect(markup).not.toContain('Recommended places to start');
  });
});
