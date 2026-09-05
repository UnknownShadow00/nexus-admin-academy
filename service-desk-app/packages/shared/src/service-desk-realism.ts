import catalog from './service-desk-realism-v1.json';
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export interface RealismCommand {
  output: string[];
  evidence?: string;
  when: Record<string, unknown>;
  set: Record<string, unknown>;
  effect: string;
}
export interface RealismFixture {
  assetTag: string;
  id: string;
  title: string;
  issue: string;
  hints: string[];
  noteFacts: string[][];
  finalConditions: Record<string, unknown>;
  initial: Record<string, unknown>;
  categories: Record<string, string[]>;
  commands: Record<string, RealismCommand[]>;
  completion: { rootCause: string; whatFixed: string; whyItWorked: string };
}
export const REALISM_FIXTURES: Readonly<Record<string, RealismFixture>> =
  catalog;
export function realismFixture(assetTag: string) {
  return Object.values(REALISM_FIXTURES).find(
    (entry) => entry.assetTag === assetTag,
  );
}
export function realismNoteComplete(fixture: RealismFixture, text: string) {
  return fixture.noteFacts.every((alternatives) =>
    alternatives.some((fact) => text.toLowerCase().includes(fact)),
  );
}

export function readStatePath(state: unknown, path: string): unknown {
  return path
    .split('/')
    .reduce<unknown>(
      (value, key) =>
        value && typeof value === 'object'
          ? (value as Record<string, unknown>)[key]
          : undefined,
      state,
    );
}
export function writeStatePath(state: object, path: string, value: unknown) {
  const keys = path.split('/');
  let target = state as Record<string, unknown>;
  for (const key of keys.slice(0, -1)) {
    target[key] ??= {};
    target = target[key] as Record<string, unknown>;
  }
  target[keys.at(-1)!] = clone(value);
}
export function mergeFixtureState<T extends object>(
  state: T,
  patch: Record<string, unknown>,
): T {
  const next = clone(state);
  const merge = (
    target: Record<string, unknown>,
    source: Record<string, unknown>,
  ) => {
    for (const [key, value] of Object.entries(source)) {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        target[key] ??= {};
        merge(
          target[key] as Record<string, unknown>,
          value as Record<string, unknown>,
        );
      } else target[key] = clone(value);
    }
  };
  merge(next as Record<string, unknown>, patch);
  return next;
}

/** Bounded declarative operations; never executes a host shell. The server
 * replays these same immutable fixture rules from its trusted ledger. */
export function runRealismCommand<T extends object>(
  state: T,
  fixture: RealismFixture,
  command: string,
) {
  const key = Object.keys(fixture.commands).find(
    (entry) => entry.toLowerCase() === command.trim().toLowerCase(),
  );
  const rule =
    key &&
    fixture.commands[key]?.find((candidate) =>
      Object.entries(candidate.when).every(
        ([path, expected]) =>
          JSON.stringify(readStatePath(state, path)) ===
          JSON.stringify(expected),
      ),
    );
  const next = clone(state);
  writeStatePath(next, 'realism/lastEvidence', null);
  if (!rule)
    return {
      state: next,
      output: [
        'Command or target unavailable in this assigned support scope. Run help for supported syntax.',
      ],
      success: false,
    };
  if (rule.effect === 'rejected')
    return { state: next, output: rule.output, success: false };
  for (const [path, value] of Object.entries(rule.set))
    writeStatePath(next, path, value);
  const usageNodes = readStatePath(next, 'storage/usageNodeIds');
  if (Array.isArray(usageNodes)) {
    const used = usageNodes.reduce<number>(
      (total, id: string) =>
        total + Number(readStatePath(next, `filesystem/nodes/${id}/sizeBytes`)),
      Number(readStatePath(next, 'storage/fixedUsedBytes')),
    );
    writeStatePath(
      next,
      'storage/freeBytes',
      Number(readStatePath(next, 'storage/capacityBytes')) - used,
    );
  }
  if (rule.effect === 'repair') {
    writeStatePath(next, 'realism/changed', true);
    writeStatePath(next, 'realism/repaired', true);
  }
  if (rule.effect === 'harmful') writeStatePath(next, 'realism/harmful', true);
  const preChangeEvidence = [
    ...(fixture.categories.investigation ?? []),
    ...(fixture.categories.diagnosis ?? []),
  ];
  if (
    rule.evidence &&
    !(
      readStatePath(state, 'realism/changed') &&
      preChangeEvidence.includes(rule.evidence)
    )
  ) {
    writeStatePath(next, `realism/observed/${rule.evidence}`, true);
    writeStatePath(next, 'realism/lastEvidence', rule.evidence);
  }
  const output = rule.output.map((line) =>
    line.replace(/\{([^}]+)\}/g, (_, path: string) => {
      const value = readStatePath(next, path);
      return Array.isArray(value) ? value.join(', ') : String(value);
    }),
  );
  return { state: next, output, success: true };
}
