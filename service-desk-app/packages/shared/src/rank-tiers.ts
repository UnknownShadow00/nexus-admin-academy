export interface RankTier {
  name: string;
  points: number;
}

export const RANK_TIERS = [
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
] as const satisfies readonly RankTier[];

export interface RankProgress {
  currentTier: (typeof RANK_TIERS)[number]['name'];
  nextTier: (typeof RANK_TIERS)[number]['name'] | null;
  pointsRemaining: number;
}

export function getRankForPoints(points: number): RankProgress {
  const normalizedPoints = Number.isFinite(points)
    ? Math.max(0, Math.floor(points))
    : 0;
  let currentIndex = 0;

  for (let index = 1; index < RANK_TIERS.length; index += 1) {
    if (normalizedPoints < RANK_TIERS[index]!.points) {
      break;
    }
    currentIndex = index;
  }

  const currentTier = RANK_TIERS[currentIndex]!;
  const nextTier = RANK_TIERS[currentIndex + 1] ?? null;

  return {
    currentTier: currentTier.name,
    nextTier: nextTier?.name ?? null,
    pointsRemaining: nextTier
      ? Math.max(0, nextTier.points - normalizedPoints)
      : 0,
  };
}
