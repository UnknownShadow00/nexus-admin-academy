import { describe, expect, it } from 'vitest';

import { RANK_TIERS, getRankForPoints } from './rank-tiers';

describe('rank tiers', () => {
  it('defines the complete eleven-rung points ladder', () => {
    expect(RANK_TIERS).toEqual([
      { name: 'Rookie', points: 0 },
      { name: 'Bronze', points: 100 },
      { name: 'Silver', points: 300 },
      { name: 'Gold', points: 750 },
      { name: 'Platinum', points: 1_500 },
      { name: 'Diamond', points: 3_000 },
      { name: 'Master', points: 6_000 },
      { name: 'Legend', points: 10_000 },
      { name: 'Mythic', points: 15_000 },
      { name: 'Apex', points: 25_000 },
      { name: 'Eternal', points: 50_000 },
    ]);
  });

  it('returns progress within and at the boundaries of a tier', () => {
    expect(getRankForPoints(99)).toEqual({
      currentTier: 'Rookie',
      nextTier: 'Bronze',
      pointsRemaining: 1,
    });
    expect(getRankForPoints(300)).toEqual({
      currentTier: 'Silver',
      nextTier: 'Gold',
      pointsRemaining: 450,
    });
  });

  it('clamps invalid totals and reports the max tier as complete', () => {
    expect(getRankForPoints(-50).currentTier).toBe('Rookie');
    expect(getRankForPoints(Number.NaN).pointsRemaining).toBe(100);
    expect(getRankForPoints(60_000)).toEqual({
      currentTier: 'Eternal',
      nextTier: null,
      pointsRemaining: 0,
    });
  });
});
