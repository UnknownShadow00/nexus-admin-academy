import { describe, expect, it } from 'vitest';

import { attemptsRemaining, experienceModeLabel } from './TicketContextBar';

describe('TicketContextBar helpers', () => {
  it('maps every assignment mode to student-facing copy', () => {
    expect(experienceModeLabel('guided')).toBe('Guided Practice');
    expect(experienceModeLabel('practice')).toBe('Practice');
    expect(experienceModeLabel('assessment')).toBe('Assessment');
  });

  it('only calculates attempts when a maximum exists', () => {
    expect(attemptsRemaining(null, 2)).toBeNull();
    expect(attemptsRemaining(3, 2)).toBe(2);
  });
});
