export interface LeaderboardFixture {
  id: string;
  name: string;
  points: number;
}

/**
 * Illustrative cohort flavor for the client-only leaderboard. The live student
 * row is added separately from the persisted attempt.
 */
export const LEADERBOARD_FIXTURES = [
  { id: 'fixture-morgan', name: 'Morgan K.', points: 1_840 },
  { id: 'fixture-riley', name: 'Riley T.', points: 920 },
  { id: 'fixture-jordan', name: 'Jordan P.', points: 440 },
  { id: 'fixture-sam', name: 'Sam D.', points: 180 },
] as const satisfies readonly LeaderboardFixture[];
