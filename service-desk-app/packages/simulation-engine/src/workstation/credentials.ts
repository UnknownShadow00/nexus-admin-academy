import type { WorkstationState } from '@service-desk/shared';

const SAFE_TARGET = /^[a-z0-9.-]+$/i;
const SAFE_USERNAME = /^[a-z0-9._@\\-]+$/i;

export function addWorkstationCredential(
  state: WorkstationState,
  targetInput: string,
  usernameInput: string,
  timestamp: string,
): { state: WorkstationState; error: string | null } {
  const target = targetInput.trim().toLowerCase();
  const username = usernameInput.trim();
  if (!target || !SAFE_TARGET.test(target)) {
    return { state, error: 'Enter a valid credential target hostname.' };
  }
  if (!username || !SAFE_USERNAME.test(username)) {
    return { state, error: 'Enter a valid synthetic domain username.' };
  }
  return {
    state: {
      ...state,
      credentials: {
        ...state.credentials,
        [target]: {
          id: `credential-${target.replace(/[^a-z0-9]+/g, '-')}`,
          target,
          username,
          type: 'domain-password',
          persistence: 'local-machine',
          createdAt: timestamp,
        },
      },
    },
    error: null,
  };
}

export function deleteWorkstationCredential(
  state: WorkstationState,
  targetInput: string,
): { state: WorkstationState; error: string | null } {
  const target = targetInput.trim().toLowerCase();
  if (!state.credentials[target]) {
    return { state, error: 'That stored credential does not exist.' };
  }
  const credentials = { ...state.credentials };
  delete credentials[target];
  const mappedDrives = Object.fromEntries(
    Object.entries(state.mappedDrives).map(([letter, drive]) => [
      letter,
      drive.credentialTarget === target
        ? { ...drive, credentialTarget: null }
        : drive,
    ]),
  );
  return {
    state: { ...state, credentials, mappedDrives },
    error: null,
  };
}
