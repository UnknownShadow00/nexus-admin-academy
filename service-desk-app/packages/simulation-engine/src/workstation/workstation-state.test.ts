import { describe, expect, it } from 'vitest';

import { createWorkstationState, migrateLegacyWorkstationState } from './state';

describe('shared workstation state', () => {
  it('creates one coherent machine, network, filesystem, mapping, VPN, credential, service, and window model', () => {
    const state = createWorkstationState('NX-2047');

    expect(state.schemaVersion).toBe(2);
    expect(state.machine).toMatchObject({
      assetTag: 'NX-2047',
      hostname: 'PM-LT-41',
      domain: 'NEXUS',
      domainJoinState: 'joined',
      signedInUser: 'NEXUS\\harper.kim',
    });
    expect(state.network.interfaces[0]).toMatchObject({
      alias: 'Wi-Fi',
      status: 'limited',
      ipv4: { address: '10.24.47.18', dhcpEnabled: true },
    });
    expect(state.network.vpn.profiles['nexus-secure']).toMatchObject({
      name: 'Nexus Secure Access',
      serverAddress: 'vpn.nexus.example',
      requiredCompliance: 'compliant',
    });
    expect(state.mappedDrives['Z:']).toMatchObject({
      letter: 'Z:',
      uncPath: '\\\\partner.nexus.internal\\workspace',
      reconnectAtSignIn: true,
      status: 'network-path-error',
    });
    expect(state.filesystem.nodes['drive-Z']).toMatchObject({
      kind: 'drive',
      path: 'Z:\\',
    });
    expect(state.services['VPN Client Service']).toMatchObject({
      state: 'running',
      startupType: 'automatic',
    });
    expect(state.credentials).toEqual({});
    expect(state.desktop).toMatchObject({
      activeAppId: null,
      startMenuOpen: false,
    });
  });

  it('migrates legacy overlay facts without inventing success or credentials', () => {
    const migrated = migrateLegacyWorkstationState('NX-2047', {
      dnsServers: ['192.0.2.53'],
      driveStates: { 'C:': 'connected', 'Z:': 'permission-error' },
      serviceStates: { 'VPN Client Service': 'stopped' },
      vpnStatus: 'error',
      vpnError: 'Authentication failed.',
      vpnLog: [
        {
          message: 'The gateway rejected the connection.',
          timestamp: '2026-07-30T10:30:00.000Z',
        },
      ],
      openApps: ['vpn', 'explorer'],
      minimizedApps: ['explorer'],
      focusedApp: 'vpn',
      terminalHistory: [
        {
          command: 'net use',
          output: ['Z: Disconnected'],
          timestamp: '2026-07-30T10:31:00.000Z',
        },
      ],
    });

    expect(migrated.schemaVersion).toBe(2);
    expect(migrated.network.interfaces[0]?.dnsServers).toEqual(['192.0.2.53']);
    expect(migrated.mappedDrives['Z:']?.status).toBe('permission-error');
    expect(migrated.services['VPN Client Service']?.state).toBe('stopped');
    expect(migrated.network.vpn).toMatchObject({
      status: 'error',
      error: {
        code: 'legacy-error',
        message: 'Authentication failed.',
      },
    });
    expect(migrated.desktop.windows.explorer).toMatchObject({
      open: true,
      minimized: true,
    });
    expect(migrated.desktop.windows.vpn).toMatchObject({
      open: true,
      minimized: false,
    });
    expect(migrated.desktop.activeAppId).toBe('vpn');
    expect(migrated.terminal.history).toHaveLength(1);
    expect(migrated.credentials).toEqual({});
  });

  it('rejects an unknown workstation instead of fabricating a fixture', () => {
    expect(() => createWorkstationState('NX-DOES-NOT-EXIST')).toThrow(
      'Missing workstation fixture for NX-DOES-NOT-EXIST.',
    );
  });
});
