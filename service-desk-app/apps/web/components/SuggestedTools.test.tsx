import { TicketCategory } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { SuggestedTools } from './SuggestedTools';

describe('SuggestedTools ticket context', () => {
  it('keeps the actual ticket id on tool links', () => {
    const markup = renderToStaticMarkup(<SuggestedTools experienceMode="guided" ticketCategory={TicketCategory.Network} ticketId="INC2510" toolSlugs={['remote-desktop', 'documentation']} />);
    expect(markup).toContain('/tools/remote-desktop?ticket=INC2510');
    expect(markup).toContain('ticket=INC2510');
    expect(markup).not.toContain('INC2406');
  });
});
