import { describe, expect, it } from 'vitest';

import { executeWorkstationCommand } from './commands';
import { createWorkstationState, reconcileWorkstationState } from './state';

const NOW = '2026-07-30T10:30:00.000Z';

describe('deterministic workstation command interpreter', () => {
  it('derives ipconfig output from the shared interface state', () => {
    const state = createWorkstationState('NX-2047');
    const result = executeWorkstationCommand(state, 'ipconfig /all', NOW);

    expect(result.output.join('\n')).toContain('Wireless LAN adapter Wi-Fi');
    expect(result.output.join('\n')).toContain('10.24.47.18');
    expect(result.output.join('\n')).toContain('10.20.0.10');
    expect(result.state).toEqual(state);
  });

  it('requires VPN reachability before mapping the partner UNC path', () => {
    const initial = createWorkstationState('NX-2047');
    const blocked = executeWorkstationCommand(
      initial,
      'net use Z: "\\\\partner.nexus.internal\\workspace" /persistent:yes',
      NOW,
    );
    const vpnConnected = reconcileWorkstationState(initial, {
      vpnStatus: 'connected',
    });
    const mapped = executeWorkstationCommand(
      vpnConnected,
      'net use Z: "\\\\partner.nexus.internal\\workspace" /persistent:yes',
      NOW,
    );

    expect(blocked.success).toBe(false);
    expect(blocked.output.join('\n')).toContain('network path was not found');
    expect(blocked.state.mappedDrives['Z:']?.status).toBe('network-path-error');
    expect(mapped.success).toBe(true);
    expect(mapped.state.mappedDrives['Z:']).toMatchObject({
      uncPath: '\\\\partner.nexus.internal\\workspace',
      reconnectAtSignIn: true,
      status: 'connected',
    });
    expect(mapped.state.filesystem.nodes['drive-Z']).toMatchObject({
      available: true,
      access: 'read-write',
    });
  });

  it('deletes a mapping without changing unrelated drives', () => {
    const initial = reconcileWorkstationState(
      createWorkstationState('NX-2047'),
      { vpnStatus: 'connected', driveStates: { 'Z:': 'connected' } },
    );
    const result = executeWorkstationCommand(
      initial,
      'net use Z: /delete',
      NOW,
    );

    expect(result.success).toBe(true);
    expect(result.state.mappedDrives['Z:']).toBeUndefined();
    expect(result.state.filesystem.nodes['drive-Z']).toBeUndefined();
    expect(result.output[0]).toContain('deleted successfully');
  });

  it('adds, lists, and deletes safe credential metadata without a password field', () => {
    const initial = createWorkstationState('NX-2047');
    const added = executeWorkstationCommand(
      initial,
      'cmdkey /add:partner.nexus.internal /user:NEXUS\\harper.kim',
      NOW,
    );
    const listed = executeWorkstationCommand(added.state, 'cmdkey /list', NOW);
    const removed = executeWorkstationCommand(
      listed.state,
      'cmdkey /delete:partner.nexus.internal',
      NOW,
    );

    expect(added.success).toBe(true);
    expect(added.state.credentials['partner.nexus.internal']).toMatchObject({
      target: 'partner.nexus.internal',
      username: 'NEXUS\\harper.kim',
      persistence: 'local-machine',
    });
    expect(
      Object.prototype.hasOwnProperty.call(
        added.state.credentials['partner.nexus.internal'],
        'password',
      ),
    ).toBe(false);
    expect(listed.output.join('\n')).toContain('partner.nexus.internal');
    expect(listed.output.join('\n')).toContain('NEXUS\\harper.kim');
    expect(removed.state.credentials).toEqual({});
  });

  it('mutates the same service state used by the Services app', () => {
    const initial = createWorkstationState('NX-4419');
    const started = executeWorkstationCommand(
      initial,
      'net start "Print Spooler"',
      NOW,
    );
    const queried = executeWorkstationCommand(
      started.state,
      'sc query "Print Spooler"',
      NOW,
    );

    expect(started.state.services['Print Spooler']?.state).toBe('running');
    expect(queried.output.join('\n')).toContain('4  RUNNING');
  });

  it('flushes modeled DNS cache and rejects shell metacharacters', () => {
    const initial = {
      ...createWorkstationState('NX-2047'),
      network: {
        ...createWorkstationState('NX-2047').network,
        dnsCache: [
          {
            hostname: 'partner.nexus.internal',
            address: '10.90.20.15',
            expiresAt: '2026-07-30T11:00:00.000Z',
            source: 'query' as const,
          },
        ],
      },
    };
    const flushed = executeWorkstationCommand(
      initial,
      'ipconfig /flushdns',
      NOW,
    );
    const injection = executeWorkstationCommand(
      flushed.state,
      'hostname & whoami',
      NOW,
    );

    expect(flushed.state.network.dnsCache).toEqual([]);
    expect(injection.success).toBe(false);
    expect(injection.output[0]).toContain('unsupported characters');
  });

  it.each([
    'hostname && whoami',
    'hostname || whoami',
    'hostname | whoami',
    'hostname > output.txt',
    'hostname < input.txt',
    'hostname; whoami',
    'hostname\nwhoami',
    'echo `whoami`',
    'echo $(whoami)',
  ])('rejects chaining, redirect, and substitution syntax: %s', (command) => {
    const initial = createWorkstationState('NX-2047');
    const result = executeWorkstationCommand(initial, command, NOW);

    expect(result.success).toBe(false);
    expect(result.state).toEqual(initial);
    expect(result.output.join('\n')).toMatch(
      /unsupported|could not be parsed/i,
    );
  });

  it('handles whitespace, quoting, mixed case, Unicode, and traversal strings deterministically', () => {
    const initial = createWorkstationState('NX-4419');

    expect(
      executeWorkstationCommand(
        initial,
        '  SC   QuErY   "Print Spooler"  ',
        NOW,
      ).output.join('\n'),
    ).toContain('SERVICE_NAME: Print Spooler');
    expect(
      executeWorkstationCommand(initial, 'sc query "Print Spooler', NOW)
        .success,
    ).toBe(false);
    expect(executeWorkstationCommand(initial, 'hostname ☃', NOW).success).toBe(
      false,
    );
    expect(
      executeWorkstationCommand(initial, 'net use Z: ..\\..\\etc', NOW).success,
    ).toBe(false);
  });

  it('rejects unsupported switches, surplus arguments, controls, and oversized input', () => {
    const initial = createWorkstationState('NX-2047');

    for (const command of [
      'ipconfig /all /verbose',
      'ping example.com /unknown',
      'whoami /all',
      `hostname\u0000`,
      'a'.repeat(513),
    ]) {
      const result = executeWorkstationCommand(initial, command, NOW);
      expect(result.success, command).toBe(false);
      expect(result.state, command).toEqual(initial);
    }
  });
});
