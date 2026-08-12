import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import { restoreAttempt, serializeAttempt } from './serialize';

const ACTOR_ID = 'student-1';

function apply(
  attempt: ReturnType<typeof createAttempt>,
  action: SimulationAction,
) {
  return applyAction(attempt, ACTOR_ID, action);
}

describe('Server Room actions', () => {
  it('restarts a device and rejects an unknown device with one event each', () => {
    const restarted = apply(createAttempt(), {
      type: 'server_room.restart_device',
      payload: { nodeId: 'core-router' },
    });
    const rejected = apply(restarted.attempt, {
      type: 'server_room.restart_device',
      payload: { nodeId: 'missing-device' },
    });

    expect(restarted.event.success).toBe(true);
    expect(restarted.attempt.serverRoomOverlays['core-router']?.status).toBe(
      'online',
    );
    expect(
      restarted.attempt.serverRoomOverlays['core-router']?.events,
    ).toHaveLength(1);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.serverRoomOverlays['missing-device']?.events,
    ).toHaveLength(1);
  });

  it('restarts a named server service and rejects an unknown server', () => {
    const restarted = apply(createAttempt(), {
      type: 'server_room.restart_service',
      payload: { nodeId: 'print01', serviceName: 'Print Spooler' },
    });
    const rejected = apply(restarted.attempt, {
      type: 'server_room.restart_service',
      payload: {
        nodeId: 'missing-server',
        serviceName: 'Print Spooler',
      },
    });

    expect(restarted.event.success).toBe(true);
    expect(
      restarted.attempt.serverRoomOverlays.print01?.serviceStates[
        'Print Spooler'
      ],
    ).toBe('running');
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.serverRoomOverlays['missing-server']?.events,
    ).toHaveLength(1);
  });

  it('rejects a service that is not present on a valid server', () => {
    const rejected = apply(createAttempt(), {
      type: 'server_room.restart_service',
      payload: { nodeId: 'dc01', serviceName: 'Print Spooler' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('not a simulated service');
    expect(rejected.attempt.serverRoomOverlays.dc01?.events).toHaveLength(1);
  });

  it('restarts a server and rejects an unknown server with one event each', () => {
    const restarted = apply(createAttempt(), {
      type: 'server_room.restart_server',
      payload: { nodeId: 'dc01' },
    });
    const rejected = apply(restarted.attempt, {
      type: 'server_room.restart_server',
      payload: { nodeId: 'missing-server' },
    });

    expect(restarted.event.success).toBe(true);
    expect(restarted.attempt.serverRoomOverlays.dc01?.status).toBe('online');
    expect(restarted.attempt.serverRoomOverlays.dc01?.events).toHaveLength(1);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.serverRoomOverlays['missing-server']?.events,
    ).toHaveLength(1);
  });
});

describe('Remote Desktop actions', () => {
  function connect(
    attempt: ReturnType<typeof createAttempt>,
    assetTag: string,
    ticketId: string,
  ) {
    const connecting = apply(attempt, {
      type: 'remote_desktop.connect',
      payload: { assetTag, ticketId },
    });
    const login = apply(connecting.attempt, {
      type: 'remote_desktop.begin_login',
      payload: { assetTag, ticketId },
    });
    return apply(login.attempt, {
      type: 'remote_desktop.authenticate',
      payload: {
        assetTag,
        ticketId,
        usernameEntered: true,
        passwordEntered: true,
      },
    });
  }

  function performSteps(
    attempt: ReturnType<typeof createAttempt>,
    assetTag: string,
    ticketId: string,
    steps: readonly string[],
  ) {
    return steps.reduce(
      (current, stepId) =>
        apply(current.attempt, {
          type: 'remote_desktop.perform_scenario_step',
          payload: { assetTag, ticketId, stepId },
        }),
      { attempt } as ReturnType<typeof apply>,
    );
  }

  it('connects through the login gate, cancels safely, and reconnects', () => {
    const initial = createAttempt();
    const connecting = apply(initial, {
      type: 'remote_desktop.connect',
      payload: { assetTag: 'NX-2047', ticketId: 'INC2406' },
    });
    const cancelled = apply(connecting.attempt, {
      type: 'remote_desktop.cancel_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const connected = connect(cancelled.attempt, 'NX-2047', 'INC2406');
    const disconnected = apply(connected.attempt, {
      type: 'remote_desktop.disconnect',
      payload: { assetTag: 'NX-2047' },
    });

    expect(
      cancelled.attempt.remoteDesktopOverlays['NX-2047']?.connectionState,
    ).toBe('disconnected');
    expect(
      connected.attempt.remoteDesktopOverlays['NX-2047']?.connectionState,
    ).toBe('connected');
    expect(disconnected.attempt.remoteDesktopOverlays['NX-2047']).toMatchObject(
      {
        connectionState: 'disconnected',
        openApps: [],
      },
    );
    expect(
      disconnected.attempt.remoteDesktopOverlays['NX-2047']?.events,
    ).toHaveLength(6);
  });

  it('rejects a wrong machine at the login gate and records a useful error', () => {
    const wrongMachine = connect(createAttempt(), 'NX-1344', 'INC2406');

    expect(wrongMachine.event.success).toBe(false);
    expect(wrongMachine.event.rejectReason).toContain(
      'not the affected machine',
    );
    expect(wrongMachine.attempt.remoteDesktopOverlays['NX-1344']).toMatchObject(
      {
        connectionState: 'error',
        lastError: expect.stringContaining('not the affected machine'),
      },
    );
  });

  it('persists focused application state and restores it after a refresh', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const opened = apply(connected.attempt, {
      type: 'remote_desktop.open_app',
      payload: { assetTag: 'NX-2047', appId: 'vpn' },
    });
    const minimized = apply(opened.attempt, {
      type: 'remote_desktop.minimize_app',
      payload: { assetTag: 'NX-2047', appId: 'vpn' },
    });
    const restored = apply(minimized.attempt, {
      type: 'remote_desktop.focus_app',
      payload: { assetTag: 'NX-2047', appId: 'vpn' },
    });

    const afterRefresh = restoreAttempt(serializeAttempt(restored.attempt));

    if (!afterRefresh)
      throw new Error('Expected a serialized remote desktop attempt');
    expect(afterRefresh.remoteDesktopOverlays['NX-2047']).toMatchObject({
      focusedApp: 'vpn',
      minimizedApps: [],
      openApps: ['vpn'],
    });
  });

  it('projects desktop, network, service, drive, and terminal changes into one workstation model', () => {
    const connected = connect(createAttempt(), 'NX-6128', 'INC2405');
    const explorer = apply(connected.attempt, {
      type: 'remote_desktop.open_app',
      payload: { assetTag: 'NX-6128', appId: 'explorer' },
    });
    const mapped = apply(explorer.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-6128', driveLetter: 'Y:' },
    });
    const stopped = apply(mapped.attempt, {
      type: 'remote_desktop.stop_service',
      payload: { assetTag: 'NX-6128', serviceName: 'Windows Update' },
    });
    const terminal = apply(stopped.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-6128', command: 'net use' },
    });
    const state =
      terminal.attempt.remoteDesktopOverlays['NX-6128']?.workstation;

    expect(state).toMatchObject({
      mappedDrives: { 'Y:': { status: 'connected' } },
      services: { 'Windows Update': { state: 'stopped' } },
      desktop: {
        activeAppId: 'explorer',
        windows: { explorer: { open: true, minimized: false } },
      },
      terminal: { history: [{ command: 'net use' }] },
    });
    expect(state?.filesystem.nodes['drive-Y']).toMatchObject({
      available: true,
      access: 'read-write',
    });
  });

  it('persists bounded window movement, maximize/restore, and Start state', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const opened = apply(connected.attempt, {
      type: 'remote_desktop.open_app',
      payload: { assetTag: 'NX-2047', appId: 'explorer' },
    });
    const moved = apply(opened.attempt, {
      type: 'remote_desktop.move_window',
      payload: {
        assetTag: 'NX-2047',
        appId: 'explorer',
        bounds: { x: 180, y: 96, width: 820, height: 560 },
      },
    });
    const maximized = apply(moved.attempt, {
      type: 'remote_desktop.toggle_window_maximize',
      payload: { assetTag: 'NX-2047', appId: 'explorer' },
    });
    const startOpen = apply(maximized.attempt, {
      type: 'remote_desktop.set_start_menu',
      payload: { assetTag: 'NX-2047', open: true },
    });
    const restored = apply(startOpen.attempt, {
      type: 'remote_desktop.toggle_window_maximize',
      payload: { assetTag: 'NX-2047', appId: 'explorer' },
    });
    const rejected = apply(restored.attempt, {
      type: 'remote_desktop.move_window',
      payload: {
        assetTag: 'NX-2047',
        appId: 'explorer',
        bounds: { x: -10, y: 0, width: 200, height: 100 },
      },
    });

    expect(
      moved.attempt.remoteDesktopOverlays['NX-2047']?.workstation.desktop,
    ).toMatchObject({
      windows: {
        explorer: {
          bounds: { x: 180, y: 96, width: 820, height: 560 },
        },
      },
    });
    expect(
      maximized.attempt.remoteDesktopOverlays['NX-2047']?.workstation.desktop
        .windows.explorer,
    ).toMatchObject({ maximized: true, restoreBounds: { x: 180, y: 96 } });
    expect(
      startOpen.attempt.remoteDesktopOverlays['NX-2047']?.workstation.desktop
        .startMenuOpen,
    ).toBe(true);
    expect(
      restored.attempt.remoteDesktopOverlays['NX-2047']?.workstation.desktop
        .windows.explorer,
    ).toMatchObject({
      maximized: false,
      bounds: { x: 180, y: 96, width: 820, height: 560 },
      restoreBounds: null,
    });
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain(
      'within the simulated desktop',
    );
  });

  it('tracks VPN repair evidence without completing before note and closure', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const incorrect = apply(connected.attempt, {
      type: 'remote_desktop.perform_scenario_step',
      payload: {
        assetTag: 'NX-2047',
        ticketId: 'INC2406',
        stepId: 'explorer.remove-share',
      },
    });
    const inspected = apply(incorrect.attempt, {
      type: 'remote_desktop.open_app',
      payload: { assetTag: 'NX-2047', appId: 'vpn' },
    });
    const tested = apply(inspected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-2047', path: 'Z:\\' },
    });
    const connecting = apply(tested.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const fixed = apply(connecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const reconnected = apply(fixed.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-2047', driveLetter: 'Z:' },
    });
    const verified = apply(reconnected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-2047', path: 'Z:\\' },
    });

    expect(incorrect.event.success).toBe(false);
    expect(incorrect.event.rejectReason).toContain('does not address');
    expect(
      verified.attempt.remoteDesktopOverlays['NX-2047']?.completedScenarioIds,
    ).not.toContain('vpn-shared-drive');
    expect(
      verified.attempt.remoteDesktopOverlays['NX-2047']?.scenarioProgress[
        'vpn-shared-drive'
      ]?.phases,
    ).toMatchObject({ diagnosed: true, fixed: true, verified: true });
  });

  it('records legacy repair clicks without granting completion before evidence and closure', () => {
    const pdf = performSteps(
      connect(createAttempt(), 'NX-3560', 'INC2403').attempt,
      'NX-3560',
      'INC2403',
      ['updates.install', 'system.restart-pdf-helper', 'browser.retry-export'],
    );
    const profile = performSteps(
      connect(createAttempt(), 'NX-4831', 'INC2401').attempt,
      'NX-4831',
      'INC2401',
      ['settings.clear-profile-storage', 'browser.retry-sign-in'],
    );

    expect(
      pdf.attempt.remoteDesktopOverlays['NX-3560']?.completedScenarioIds,
    ).not.toContain('pdf-export-update');
    expect(
      profile.attempt.remoteDesktopOverlays['NX-4831']?.completedScenarioIds,
    ).not.toContain('profile-storage');
  });

  it('keeps training mode as an isolated per-workstation preference', () => {
    const updated = apply(createAttempt(), {
      type: 'remote_desktop.toggle_training_mode',
      payload: { assetTag: 'NX-2047', enabled: false },
    });

    expect(updated.attempt.remoteDesktopOverlays['NX-2047']?.trainingMode).toBe(
      false,
    );
    expect(updated.attempt.remoteDesktopOverlays['NX-3560']?.trainingMode).toBe(
      true,
    );
  });

  it('restarts a workstation and rejects an unknown workstation', () => {
    const restarted = apply(createAttempt(), {
      type: 'remote_desktop.restart_computer',
      payload: { assetTag: 'NX-1344' },
    });
    const rejected = apply(restarted.attempt, {
      type: 'remote_desktop.restart_computer',
      payload: { assetTag: 'NX-0000' },
    });

    expect(restarted.event.success).toBe(true);
    expect(restarted.attempt.remoteDesktopOverlays['NX-1344']?.powerState).toBe(
      'online',
    );
    expect(
      restarted.attempt.remoteDesktopOverlays['NX-1344']?.events,
    ).toHaveLength(1);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-0000']?.events,
    ).toHaveLength(1);
  });

  it('resets workstation network state and rejects an unknown workstation', () => {
    const reset = apply(createAttempt(), {
      type: 'remote_desktop.network_reset',
      payload: { assetTag: 'NX-2014' },
    });
    const rejected = apply(reset.attempt, {
      type: 'remote_desktop.network_reset',
      payload: { assetTag: 'NX-0000' },
    });

    expect(reset.event.success).toBe(true);
    expect(reset.attempt.remoteDesktopOverlays['NX-2014']?.networkStatus).toBe(
      'online',
    );
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-0000']?.events,
    ).toHaveLength(1);
  });

  it('restarts a simulated service and rejects an unknown workstation', () => {
    const restarted = apply(createAttempt(), {
      type: 'remote_desktop.restart_service',
      payload: { assetTag: 'NX-3560', serviceName: 'Windows Update' },
    });
    const rejected = apply(restarted.attempt, {
      type: 'remote_desktop.restart_service',
      payload: { assetTag: 'NX-0000', serviceName: 'Windows Update' },
    });

    expect(restarted.event.success).toBe(true);
    expect(
      restarted.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates[
        'Windows Update'
      ],
    ).toBe('running');
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not exist');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-0000']?.events,
    ).toHaveLength(1);
  });

  it('rejects a service that is not present on a valid workstation', () => {
    const rejected = apply(createAttempt(), {
      type: 'remote_desktop.restart_service',
      payload: { assetTag: 'NX-4831', serviceName: 'Domain Services' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('not a simulated service');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-4831']?.events,
    ).toHaveLength(1);
  });

  it('runs every supported Terminal command with deterministic state-derived output', () => {
    const vpn = connect(createAttempt(), 'NX-2047', 'INC2406');
    const mappedDrive = connect(createAttempt(), 'NX-6128', 'INC2405');
    const network = connect(createAttempt(), 'NX-7714', 'INC2402');
    const service = connect(createAttempt(), 'NX-3560', 'INC2403');
    const terminal = (
      current: ReturnType<typeof apply>,
      assetTag: string,
      command: string,
    ) =>
      apply(current.attempt, {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag, command },
      });

    expect(terminal(vpn, 'NX-2047', 'ipconfig').event.success).toBe(true);
    expect(
      terminal(vpn, 'NX-2047', 'ipconfig /all')
        .attempt.remoteDesktopOverlays['NX-2047']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('DNS Servers');
    expect(
      terminal(network, 'NX-7714', 'ping 10.77.14.1')
        .attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('Reply from');
    expect(
      terminal(network, 'NX-7714', 'ping dns01.nexus.internal')
        .attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('could not find host');
    expect(
      terminal(network, 'NX-7714', 'nslookup dns01.nexus.internal')
        .attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('Request timed out');
    expect(
      terminal(network, 'NX-7714', 'tracert 10.77.14.1')
        .attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('Trace complete');
    expect(
      terminal(vpn, 'NX-2047', 'net use')
        .attempt.remoteDesktopOverlays['NX-2047']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('Unavailable');
    expect(
      terminal(mappedDrive, 'NX-6128', 'whoami')
        .attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('NEXUS');
    expect(
      terminal(
        mappedDrive,
        'NX-6128',
        'hostname',
      ).attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory.at(-1)
        ?.output,
    ).toEqual(['NX-6128-WKS']);
    expect(
      terminal(mappedDrive, 'NX-6128', 'gpupdate')
        .attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('completed successfully');
    expect(
      terminal(mappedDrive, 'NX-6128', 'systeminfo')
        .attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('System Model');
    expect(
      terminal(service, 'NX-3560', 'tasklist')
        .attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('PrintSpooler');
    expect(
      terminal(service, 'NX-3560', 'sc query Windows Update')
        .attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('STOPPED');
    expect(
      terminal(service, 'NX-3560', 'help')
        .attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory.at(-1)
        ?.output.join('\n'),
    ).toContain('Supported commands');
  });

  it('updates the shared service state through net start and net stop and preserves terminal history', () => {
    const connected = connect(createAttempt(), 'NX-3560', 'INC2403');
    const started = apply(connected.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-3560', command: 'net start Windows Update' },
    });
    const stopped = apply(started.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-3560', command: 'net stop Windows Update' },
    });
    const queried = apply(stopped.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-3560', command: 'sc query Windows Update' },
    });
    const afterRefresh = restoreAttempt(serializeAttempt(queried.attempt));

    expect(
      started.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates[
        'Windows Update'
      ],
    ).toBe('running');
    expect(
      stopped.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates[
        'Windows Update'
      ],
    ).toBe('stopped');
    expect(
      queried.attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory,
    ).toHaveLength(3);
    expect(
      queried.attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('STOPPED');
    expect(
      afterRefresh?.remoteDesktopOverlays['NX-3560']?.terminalHistory,
    ).toEqual(
      queried.attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory,
    );
  });

  it('changes network and mapped-drive diagnostics after their simulated repairs', () => {
    const networkConnected = connect(createAttempt(), 'NX-7714', 'INC2402');
    const networkRepaired = performSteps(
      networkConnected.attempt,
      'NX-7714',
      'INC2402',
      ['settings.repair-network'],
    );
    const dnsAfterRepair = apply(networkRepaired.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: {
        assetTag: 'NX-7714',
        command: 'nslookup dns01.nexus.internal',
      },
    });
    const driveConnected = connect(createAttempt(), 'NX-6128', 'INC2405');
    const beforeRepair = apply(driveConnected.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-6128', command: 'net use' },
    });
    const driveRepaired = performSteps(
      beforeRepair.attempt,
      'NX-6128',
      'INC2405',
      ['explorer.repair-mapping'],
    );
    const afterRepair = apply(driveRepaired.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-6128', command: 'net use' },
    });

    expect(
      dnsAfterRepair.attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('dns01.nexus.internal');
    expect(
      beforeRepair.attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('Disconnected');
    expect(
      afterRepair.attempt.remoteDesktopOverlays['NX-6128']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('OK');
  });

  it('navigates the fixed Explorer tree and rejects a path outside the fixture', () => {
    const connected = connect(createAttempt(), 'NX-3560', 'INC2403');
    const localDisk = apply(connected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-3560', path: 'C:\\' },
    });
    const users = apply(localDisk.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-3560', path: 'C:\\Users' },
    });
    const invalid = apply(users.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-3560', path: 'C:\\Not A Fixture Folder' },
    });

    expect(localDisk.event.success).toBe(true);
    expect(users.attempt.remoteDesktopOverlays['NX-3560']).toMatchObject({
      explorerCurrentPath: 'C:\\Users',
      explorerError: null,
    });
    expect(invalid.event.success).toBe(false);
    expect(invalid.event.rejectReason).toContain('not available');
  });

  it('models network-path and permission errors as distinct Explorer states', () => {
    const vpn = connect(createAttempt(), 'NX-2047', 'INC2406');
    const vpnDrive = apply(vpn.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-2047', path: 'Z:\\' },
    });
    const finance = connect(createAttempt(), 'NX-4831', 'INC2401');
    const financeDrive = apply(finance.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-4831', path: 'F:\\' },
    });
    const permissionReconnect = apply(financeDrive.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-4831', driveLetter: 'F:' },
    });

    expect(
      vpnDrive.attempt.remoteDesktopOverlays['NX-2047']?.explorerError,
    ).toMatchObject({
      kind: 'network-path-error',
      message: expect.stringContaining('Network path unavailable'),
    });
    expect(
      financeDrive.attempt.remoteDesktopOverlays['NX-4831']?.explorerError,
    ).toMatchObject({
      kind: 'permission-error',
      message: expect.stringContaining('Access denied'),
    });
    expect(permissionReconnect.event.success).toBe(false);
    expect(permissionReconnect.event.rejectReason).toContain('Access denied');
  });

  it('reconnects a mapped drive and preserves the connected state through Explorer refresh', () => {
    const connected = connect(createAttempt(), 'NX-6128', 'INC2405');
    const opened = apply(connected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-6128', path: 'Y:\\' },
    });
    const reconnected = apply(opened.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-6128', driveLetter: 'Y:' },
    });
    const refreshed = apply(reconnected.attempt, {
      type: 'remote_desktop.explorer_refresh',
      payload: { assetTag: 'NX-6128' },
    });

    expect(
      opened.attempt.remoteDesktopOverlays['NX-6128']?.explorerError?.kind,
    ).toBe('network-path-error');
    expect(reconnected.attempt.remoteDesktopOverlays['NX-6128']).toMatchObject({
      driveStates: { 'Y:': 'connected' },
      explorerCurrentPath: 'Y:\\',
      explorerError: null,
    });
    expect(refreshed.attempt.remoteDesktopOverlays['NX-6128']).toMatchObject({
      driveStates: { 'Y:': 'connected' },
      explorerError: null,
      explorerLastRefreshedAt: expect.any(String),
    });
  });

  it('maps a validated UNC path with reconnect and safe stored-credential metadata', () => {
    const connected = connect(createAttempt(), 'NX-6128', 'INC2405');
    const credential = apply(connected.attempt, {
      type: 'remote_desktop.credential_add',
      payload: {
        assetTag: 'NX-6128',
        target: 'facilities.nexus.internal',
        username: 'NEXUS\\morgan.taylor',
      },
    });
    const mapped = apply(credential.attempt, {
      type: 'remote_desktop.map_drive',
      payload: {
        assetTag: 'NX-6128',
        letter: 'Y:',
        uncPath: '\\\\facilities.nexus.internal\\calendar',
        reconnectAtSignIn: true,
        credentialTarget: 'facilities.nexus.internal',
      },
    });
    const wrongPath = apply(connected.attempt, {
      type: 'remote_desktop.map_drive',
      payload: {
        assetTag: 'NX-6128',
        letter: 'Y:',
        uncPath: 'https://facilities.nexus.internal/calendar',
        reconnectAtSignIn: true,
        credentialTarget: null,
      },
    });
    const removed = apply(mapped.attempt, {
      type: 'remote_desktop.credential_delete',
      payload: {
        assetTag: 'NX-6128',
        target: 'facilities.nexus.internal',
      },
    });

    expect(credential.event.success).toBe(true);
    expect(mapped.event.success).toBe(true);
    expect(mapped.attempt.remoteDesktopOverlays['NX-6128']).toMatchObject({
      driveStates: { 'Y:': 'connected' },
      workstation: {
        mappedDrives: {
          'Y:': {
            uncPath: '\\\\facilities.nexus.internal\\calendar',
            reconnectAtSignIn: true,
            credentialTarget: 'facilities.nexus.internal',
            status: 'connected',
          },
        },
        credentials: {
          'facilities.nexus.internal': {
            username: 'NEXUS\\morgan.taylor',
          },
        },
      },
    });
    expect(wrongPath.event.success).toBe(false);
    expect(wrongPath.event.rejectReason).toContain('network name');
    expect(
      removed.attempt.remoteDesktopOverlays['NX-6128']?.workstation.credentials,
    ).toEqual({});
    expect(
      removed.attempt.remoteDesktopOverlays['NX-6128']?.workstation
        .mappedDrives['Y:']?.credentialTarget,
    ).toBeNull();
  });

  it('converges on the same shared drive state from Explorer and the legacy repair step', () => {
    const explorerSession = connect(createAttempt(), 'NX-6128', 'INC2405');
    const explorerRepair = apply(explorerSession.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-6128', driveLetter: 'Y:' },
    });
    const legacySession = connect(createAttempt(), 'NX-6128', 'INC2405');
    const legacyRepair = apply(legacySession.attempt, {
      type: 'remote_desktop.perform_scenario_step',
      payload: {
        assetTag: 'NX-6128',
        ticketId: 'INC2405',
        stepId: 'explorer.repair-mapping',
      },
    });

    expect(
      explorerRepair.attempt.remoteDesktopOverlays['NX-6128']?.driveStates,
    ).toEqual(
      legacyRepair.attempt.remoteDesktopOverlays['NX-6128']?.driveStates,
    );
  });

  it("reports identical drive status in File Explorer and Terminal's net use output", () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const explorerBefore = apply(connected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-2047', path: 'Z:\\' },
    });
    const terminalBefore = apply(explorerBefore.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-2047', command: 'net use' },
    });
    const vpnConnecting = apply(terminalBefore.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const vpnConnected = apply(vpnConnecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const driveReconnected = apply(vpnConnected.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-2047', driveLetter: 'Z:' },
    });
    const refreshed = apply(driveReconnected.attempt, {
      type: 'remote_desktop.explorer_refresh',
      payload: { assetTag: 'NX-2047' },
    });
    const terminalAfter = apply(refreshed.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-2047', command: 'net use' },
    });

    expect(
      terminalBefore.attempt.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      driveStates: { 'Z:': 'network-path-error' },
      explorerError: { kind: 'network-path-error' },
    });
    expect(
      terminalBefore.attempt.remoteDesktopOverlays['NX-2047']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('Unavailable');
    expect(
      terminalAfter.attempt.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      driveStates: { 'Z:': 'connected' },
      explorerError: null,
    });
    expect(
      terminalAfter.attempt.remoteDesktopOverlays['NX-2047']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('OK');
  });

  it('credits phase verification when Explorer refresh confirms the repaired share', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const explorerBefore = apply(connected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-2047', path: 'Z:\\' },
    });
    const inspected = apply(explorerBefore.attempt, {
      type: 'remote_desktop.open_app',
      payload: { assetTag: 'NX-2047', appId: 'vpn' },
    });
    const vpnConnecting = apply(inspected.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const vpnConnected = apply(vpnConnecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const driveReconnected = apply(vpnConnected.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-2047', driveLetter: 'Z:' },
    });
    const refreshed = apply(driveReconnected.attempt, {
      type: 'remote_desktop.explorer_refresh',
      payload: { assetTag: 'NX-2047' },
    });

    expect(
      refreshed.attempt.remoteDesktopOverlays['NX-2047']?.scenarioProgress[
        'vpn-shared-drive'
      ]?.phases,
    ).toMatchObject({ diagnosed: true, fixed: true, verified: true });
  });

  it('records a repaired calendar mapping without auto-completing the scenario', () => {
    const connected = connect(createAttempt(), 'NX-6128', 'INC2405');
    const opened = apply(connected.attempt, {
      type: 'remote_desktop.explorer_navigate',
      payload: { assetTag: 'NX-6128', path: 'Y:\\' },
    });
    const reconnected = apply(opened.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-6128', driveLetter: 'Y:' },
    });

    expect(
      reconnected.attempt.remoteDesktopOverlays['NX-6128']
        ?.completedScenarioIds,
    ).not.toContain('facilities-calendar-mapping');
  });

  it('returns an explicit deterministic response for an unrecognized Terminal command', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const result = apply(connected.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-2047', command: 'route print' },
    });

    expect(result.event.success).toBe(true);
    expect(
      result.attempt.remoteDesktopOverlays['NX-2047']?.terminalHistory.at(-1)
        ?.output[0],
    ).toContain("'route print' is not recognized");
  });

  it('requires a connected Remote Desktop session before running Terminal commands', () => {
    const result = apply(createAttempt(), {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-2047', command: 'hostname' },
    });

    expect(result.event.success).toBe(false);
    expect(result.event.rejectReason).toContain(
      'Connect to the simulated computer',
    );
  });

  it('connects and disconnects VPN routes without magically repairing a mapped drive', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const connectingVpn = apply(connected.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const completedVpn = apply(connectingVpn.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const reconnectedDrive = apply(completedVpn.attempt, {
      type: 'remote_desktop.explorer_reconnect_drive',
      payload: { assetTag: 'NX-2047', driveLetter: 'Z:' },
    });
    const disconnectedVpn = apply(reconnectedDrive.attempt, {
      type: 'remote_desktop.vpn_disconnect',
      payload: { assetTag: 'NX-2047' },
    });

    expect(
      connectingVpn.attempt.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      vpnStatus: 'connecting',
      vpnLog: [{ timestamp: expect.any(String) }],
    });
    expect(completedVpn.attempt.remoteDesktopOverlays['NX-2047']).toMatchObject(
      {
        driveStates: { 'Z:': 'network-path-error' },
        vpnError: null,
        vpnStatus: 'connected',
        workstation: {
          network: {
            intranetReachable: true,
            routes: [
              expect.objectContaining({ source: 'dhcp' }),
              expect.objectContaining({ source: 'vpn' }),
            ],
          },
          mappedDrives: { 'Z:': { status: 'network-path-error' } },
        },
      },
    );
    expect(
      reconnectedDrive.attempt.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      driveStates: { 'Z:': 'connected' },
      workstation: { mappedDrives: { 'Z:': { status: 'connected' } } },
    });
    expect(
      restoreAttempt(serializeAttempt(completedVpn.attempt))
        ?.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      vpnLog: [
        { timestamp: expect.any(String) },
        { timestamp: expect.any(String) },
      ],
      vpnStatus: 'connected',
    });
    expect(
      disconnectedVpn.attempt.remoteDesktopOverlays['NX-2047'],
    ).toMatchObject({
      driveStates: { 'Z:': 'network-path-error' },
      vpnStatus: 'disconnected',
    });

    const mappedDrive = connect(createAttempt(), 'NX-6128', 'INC2405');
    const mappedVpnConnecting = apply(mappedDrive.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-6128' },
    });
    expect(mappedVpnConnecting.event.success).toBe(false);
    expect(mappedVpnConnecting.event.rejectReason).toContain('No VPN profile');

    const online = connect(createAttempt(), 'NX-2047', 'INC2406');
    const onlineOverlay = online.attempt.remoteDesktopOverlays['NX-2047'];
    if (!onlineOverlay) throw new Error('Expected VPN workstation');
    const offlineAttempt = {
      ...online.attempt,
      remoteDesktopOverlays: {
        ...online.attempt.remoteDesktopOverlays,
        'NX-2047': { ...onlineOverlay, networkStatus: 'offline' as const },
      },
    };
    const offlineConnecting = apply(offlineAttempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const failed = apply(offlineConnecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });

    expect(failed.event.success).toBe(false);
    expect(failed.attempt.remoteDesktopOverlays['NX-2047']).toMatchObject({
      vpnError: expect.stringContaining('no network connection'),
      vpnStatus: 'error',
    });
    expect(
      failed.attempt.remoteDesktopOverlays['NX-2047']?.vpnLog.at(-1),
    ).toMatchObject({
      message: expect.stringContaining('Connection failed'),
      timestamp: expect.any(String),
    });
  });

  it('changes DNS settings and exposes the same servers to Terminal diagnostics', () => {
    const connected = connect(createAttempt(), 'NX-7714', 'INC2402');
    const updated = apply(connected.attempt, {
      type: 'remote_desktop.settings_update_dns',
      payload: {
        assetTag: 'NX-7714',
        primaryDns: '10.20.0.10',
        secondaryDns: '10.20.0.11',
      },
    });
    const diagnosed = apply(updated.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: { assetTag: 'NX-7714', command: 'ipconfig /all' },
    });

    expect(updated.event.success).toBe(true);
    expect(updated.attempt.remoteDesktopOverlays['NX-7714']).toMatchObject({
      dnsServers: ['10.20.0.10', '10.20.0.11'],
      networkStatus: 'online',
      scenarioSteps: {
        'network-configuration': ['settings.repair-network'],
      },
    });
    expect(
      diagnosed.attempt.remoteDesktopOverlays['NX-7714']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('10.20.0.10');
  });

  it('starts, stops, and restarts services through the state Terminal queries', () => {
    const connected = connect(createAttempt(), 'NX-3560', 'INC2403');
    const started = apply(connected.attempt, {
      type: 'remote_desktop.start_service',
      payload: { assetTag: 'NX-3560', serviceName: 'Windows Update' },
    });
    const stopped = apply(started.attempt, {
      type: 'remote_desktop.stop_service',
      payload: { assetTag: 'NX-3560', serviceName: 'Windows Update' },
    });
    const restarted = apply(stopped.attempt, {
      type: 'remote_desktop.restart_service',
      payload: { assetTag: 'NX-3560', serviceName: 'Windows Update' },
    });
    const queried = apply(restarted.attempt, {
      type: 'remote_desktop.run_terminal_command',
      payload: {
        assetTag: 'NX-3560',
        command: 'sc query Windows Update',
      },
    });

    expect(
      started.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates,
    ).toMatchObject({ 'Windows Update': 'running' });
    expect(
      stopped.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates,
    ).toMatchObject({ 'Windows Update': 'stopped' });
    expect(
      restarted.attempt.remoteDesktopOverlays['NX-3560']?.serviceStates,
    ).toMatchObject({ 'Windows Update': 'running' });
    expect(
      queried.attempt.remoteDesktopOverlays['NX-3560']?.terminalHistory
        .at(-1)
        ?.output.join('\n'),
    ).toContain('RUNNING');
  });

  it('requires install, installation completion, and restart before an update is applied', () => {
    const connected = connect(createAttempt(), 'NX-3560', 'INC2403');
    const installing = apply(connected.attempt, {
      type: 'remote_desktop.update_install',
      payload: { assetTag: 'NX-3560' },
    });
    const restartRequired = apply(installing.attempt, {
      type: 'remote_desktop.update_complete_install',
      payload: { assetTag: 'NX-3560' },
    });
    const applied = apply(restartRequired.attempt, {
      type: 'remote_desktop.update_restart',
      payload: { assetTag: 'NX-3560' },
    });

    expect(
      installing.attempt.remoteDesktopOverlays['NX-3560']?.updateState,
    ).toBe('installing');
    expect(
      restartRequired.attempt.remoteDesktopOverlays['NX-3560']?.updateState,
    ).toBe('restart-required');
    expect(applied.attempt.remoteDesktopOverlays['NX-3560']).toMatchObject({
      updateInstalledAt: expect.any(String),
      updateState: 'applied',
      scenarioSteps: { 'pdf-export-update': ['updates.install'] },
    });
    expect(
      restoreAttempt(serializeAttempt(applied.attempt))?.remoteDesktopOverlays[
        'NX-3560'
      ]?.updateState,
    ).toBe('applied');
  });
});
