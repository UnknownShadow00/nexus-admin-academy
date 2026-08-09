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
    const verified = apply(fixed.attempt, {
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

  it('completes the PDF export and browser-profile workflows in order', () => {
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
    ).toContain('pdf-export-update');
    expect(
      profile.attempt.remoteDesktopOverlays['NX-4831']?.completedScenarioIds,
    ).toContain('profile-storage');
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
    const refreshed = apply(vpnConnected.attempt, {
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
    const refreshed = apply(vpnConnected.attempt, {
      type: 'remote_desktop.explorer_refresh',
      payload: { assetTag: 'NX-2047' },
    });

    expect(
      refreshed.attempt.remoteDesktopOverlays['NX-2047']?.scenarioProgress[
        'vpn-shared-drive'
      ]?.phases,
    ).toMatchObject({ diagnosed: true, fixed: true, verified: true });
  });

  it('credits scenario completion when verification happens via Explorer reconnect, not just navigate', () => {
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
    ).toContain('mapped-drive-permissions');
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

  it('connects and disconnects VPN with timestamped logs, shared-drive state, and a modeled error', () => {
    const connected = connect(createAttempt(), 'NX-2047', 'INC2406');
    const connectingVpn = apply(connected.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-2047' },
    });
    const completedVpn = apply(connectingVpn.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-2047' },
    });
    const disconnectedVpn = apply(completedVpn.attempt, {
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
        driveStates: { 'Z:': 'connected' },
        vpnError: null,
        vpnStatus: 'connected',
      },
    );
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
    const mappedVpnConnected = apply(mappedVpnConnecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-6128' },
    });
    expect(
      mappedVpnConnected.attempt.remoteDesktopOverlays['NX-6128']?.driveStates[
        'Y:'
      ],
    ).toBe('disconnected');

    const offline = connect(createAttempt(), 'NX-1344', 'INC9999');
    const offlineConnecting = apply(offline.attempt, {
      type: 'remote_desktop.vpn_connect',
      payload: { assetTag: 'NX-1344' },
    });
    const failed = apply(offlineConnecting.attempt, {
      type: 'remote_desktop.vpn_complete_connection',
      payload: { assetTag: 'NX-1344' },
    });

    expect(failed.event.success).toBe(false);
    expect(failed.attempt.remoteDesktopOverlays['NX-1344']).toMatchObject({
      vpnError: expect.stringContaining('no network connection'),
      vpnStatus: 'error',
    });
    expect(
      failed.attempt.remoteDesktopOverlays['NX-1344']?.vpnLog.at(-1),
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
