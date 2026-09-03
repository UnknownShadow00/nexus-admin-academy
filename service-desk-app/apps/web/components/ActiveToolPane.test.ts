import { describe, expect, it } from 'vitest';

import { toolContextMatchesTicket } from './ActiveToolPane';

describe('toolContextMatchesTicket', () => {
  it('allows an absent or matching ticket hint', () => {
    expect(toolContextMatchesTicket(new URLSearchParams(), 'INC2401')).toBe(
      true,
    );
    expect(
      toolContextMatchesTicket(
        new URLSearchParams('ticket=inc2401'),
        'INC2401',
      ),
    ).toBe(true);
  });

  it('rejects a tool context from another ticket', () => {
    expect(
      toolContextMatchesTicket(
        new URLSearchParams('ticket=INC2402'),
        'INC2401',
      ),
    ).toBe(false);
  });
});
