import { AssetStatus, PcShelfNetworkStatus } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import { restoreAttempt, serializeAttempt } from './serialize';

describe('attempt serialization', () => {
  it('round-trips an attempt exactly', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'ticket.add_note',
      payload: { ticketId: 'INC2402', body: 'Persisted note.' },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips directory overlays and their append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'directory.unlock_account',
      payload: { directoryUserId: 'directory-user-avery-brooks' },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips chat threads, messages, and append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'chat.send_message',
      payload: {
        contactId: 'directory-user-avery-brooks',
        body: 'Can you confirm the device involved?',
      },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips asset overlays and their append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'asset.change_status',
      payload: { assetTag: 'NX-4831', status: AssetStatus.Lost },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips PC Shelf overlays and their append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'pc_shelf.change_network_status',
      payload: {
        assetTag: 'SD9099',
        networkStatus: PcShelfNetworkStatus.Offline,
      },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips Server Room overlays and their append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'server_room.restart_service',
      payload: { nodeId: 'print01', serviceName: 'Print Spooler' },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips Remote Desktop overlays and their append-only events', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'remote_desktop.network_reset',
      payload: { assetTag: 'NX-2014' },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('migrates the legacy trainingMode boolean and back-fills phase progress', () => {
    const attempt = createAttempt({
      id: 'phase-17-attempt',
      startedAt: '2026-07-30T10:30:00.000Z',
    });
    const overlay = attempt.remoteDesktopOverlays['NX-2047'];
    if (!overlay) throw new Error('Expected remote desktop fixture');
    const {
      learningMode: _learningMode,
      scenarioProgress: _scenarioProgress,
      ...legacyOverlay
    } = overlay;
    const legacyAttempt = {
      ...attempt,
      remoteDesktopOverlays: {
        ...attempt.remoteDesktopOverlays,
        'NX-2047': { ...legacyOverlay, trainingMode: false },
      },
    };

    expect(
      restoreAttempt(JSON.stringify(legacyAttempt))?.remoteDesktopOverlays[
        'NX-2047'
      ],
    ).toMatchObject({ learningMode: 'practice', scenarioProgress: {} });
  });

  it('back-fills terminal history for a valid Phase 14 Remote Desktop overlay', () => {
    const attempt = createAttempt({
      id: 'phase-14-attempt',
      startedAt: '2026-07-30T10:30:00.000Z',
    });
    const overlay = attempt.remoteDesktopOverlays['NX-2047'];
    if (!overlay) throw new Error('Expected remote desktop fixture');
    const { terminalHistory: _terminalHistory, ...legacyOverlay } = overlay;
    const legacyAttempt = {
      ...attempt,
      remoteDesktopOverlays: {
        ...attempt.remoteDesktopOverlays,
        'NX-2047': legacyOverlay,
      },
    };

    expect(
      restoreAttempt(JSON.stringify(legacyAttempt))?.remoteDesktopOverlays[
        'NX-2047'
      ]?.terminalHistory,
    ).toEqual([]);
  });

  it('back-fills missing service states from the initial fixture state', () => {
    const attempt = createAttempt({
      id: 'legacy-service-states-attempt',
      startedAt: '2026-07-30T10:30:00.000Z',
    });
    const remoteOverlay = attempt.remoteDesktopOverlays['NX-4419'];
    const serverOverlay = attempt.serverRoomOverlays.print01;
    if (!remoteOverlay || !serverOverlay) {
      throw new Error('Expected Remote Desktop and Server Room fixtures');
    }
    const { serviceStates: _remoteServiceStates, ...legacyRemoteOverlay } =
      remoteOverlay;
    const { serviceStates: _serverServiceStates, ...legacyServerOverlay } =
      serverOverlay;
    const legacyAttempt = {
      ...attempt,
      remoteDesktopOverlays: {
        ...attempt.remoteDesktopOverlays,
        'NX-4419': legacyRemoteOverlay,
      },
      serverRoomOverlays: {
        ...attempt.serverRoomOverlays,
        print01: legacyServerOverlay,
      },
    };

    const restored = restoreAttempt(JSON.stringify(legacyAttempt));

    expect(restored?.remoteDesktopOverlays['NX-4419']?.serviceStates).toEqual(
      remoteOverlay.serviceStates,
    );
    expect(restored?.serverRoomOverlays.print01?.serviceStates).toEqual(
      serverOverlay.serviceStates,
    );
  });

  it('back-fills Phase 16 Explorer state for a persisted Phase 15 overlay', () => {
    const attempt = createAttempt({
      id: 'phase-15-attempt',
      startedAt: '2026-07-30T10:30:00.000Z',
    });
    const overlay = attempt.remoteDesktopOverlays['NX-2047'];
    if (!overlay) throw new Error('Expected remote desktop fixture');
    const {
      driveStates: _driveStates,
      explorerCurrentPath: _explorerCurrentPath,
      explorerError: _explorerError,
      explorerLastRefreshedAt: _explorerLastRefreshedAt,
      ...legacyOverlay
    } = overlay;
    const legacyAttempt = {
      ...attempt,
      remoteDesktopOverlays: {
        ...attempt.remoteDesktopOverlays,
        'NX-2047': legacyOverlay,
      },
    };

    expect(
      restoreAttempt(JSON.stringify(legacyAttempt))?.remoteDesktopOverlays[
        'NX-2047'
      ],
    ).toMatchObject({
      driveStates: { 'C:': 'connected', 'Z:': 'network-path-error' },
      explorerCurrentPath: 'This PC',
      explorerError: null,
      explorerLastRefreshedAt: null,
    });
  });

  it('persists progressive ticket hint usage across a refresh', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'ticket.reveal_hint',
      payload: { ticketId: 'INC2406', step: 1 },
    }).attempt;

    expect(
      restoreAttempt(serializeAttempt(attempt))?.ticketOverlays.INC2406,
    ).toMatchObject({ hintsRevealedCount: 1 });
  });

  it('round-trips a persisted deployment run', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'deployment.start',
      payload: {},
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('round-trips shipment records and the last shipping address', () => {
    const attempt = applyAction(createAttempt(), 'student-1', {
      type: 'shipping.create',
      payload: {
        recipientDirectoryUserId: 'directory-user-avery-brooks',
        recipientName: 'Avery Brooks',
        street: '120 Cedar Street',
        city: 'Seattle',
        state: 'WA',
        postalCode: '98101',
        senderDepartment: 'IT Department',
        equipment: [{ name: 'Monitor', quantity: 1 }],
        computerAssetTag: null,
        speed: 'standard',
        includeReturnLabel: false,
      },
    }).attempt;

    expect(restoreAttempt(serializeAttempt(attempt))).toEqual(attempt);
  });

  it('migrates a valid Phase 4 attempt without directory overlays', () => {
    const { directoryOverlays: _directoryOverlays, ...legacyAttempt } =
      createAttempt({
        id: 'legacy-attempt',
        startedAt: '2026-07-28T10:30:00.000Z',
      });

    expect(restoreAttempt(JSON.stringify(legacyAttempt))).toMatchObject({
      id: 'legacy-attempt',
      directoryOverlays: {},
      chatThreads: {},
    });
  });

  it('migrates a valid Phase 5 attempt without chat threads', () => {
    const { chatThreads: _chatThreads, ...legacyAttempt } = createAttempt({
      id: 'phase-5-attempt',
      startedAt: '2026-07-28T10:30:00.000Z',
    });

    expect(restoreAttempt(JSON.stringify(legacyAttempt))).toMatchObject({
      id: 'phase-5-attempt',
      chatThreads: {},
    });
  });

  it('migrates a valid Phase 6 attempt without asset or PC Shelf overlays', () => {
    const {
      assetOverlays: _assetOverlays,
      pcShelfOverlays: _pcShelfOverlays,
      ...legacyAttempt
    } = createAttempt({
      id: 'phase-6-attempt',
      startedAt: '2026-07-28T10:30:00.000Z',
    });

    expect(restoreAttempt(JSON.stringify(legacyAttempt))).toMatchObject({
      id: 'phase-6-attempt',
      assetOverlays: {},
      pcShelfOverlays: {
        SD9099: { present: true },
        SD8765: { present: true },
        SD7654: { present: true },
        SD6214: { present: true },
      },
    });
  });

  it('migrates a valid Phase 7 attempt without Phase 8 overlays', () => {
    const {
      remoteDesktopOverlays: _remoteDesktopOverlays,
      serverRoomOverlays: _serverRoomOverlays,
      ...legacyAttempt
    } = createAttempt({
      id: 'phase-7-attempt',
      startedAt: '2026-07-28T10:30:00.000Z',
    });

    expect(restoreAttempt(JSON.stringify(legacyAttempt))).toMatchObject({
      id: 'phase-7-attempt',
      remoteDesktopOverlays: {
        'NX-4831': { powerState: 'online' },
      },
      serverRoomOverlays: {
        dc01: { status: 'online' },
      },
    });
  });

  it('migrates a valid Phase 8 attempt without deployment or shipping state', () => {
    const {
      activeDeploymentRunId: _activeDeploymentRunId,
      deploymentRuns: _deploymentRuns,
      lastShippingAddress: _lastShippingAddress,
      shipments: _shipments,
      ...legacyAttempt
    } = createAttempt({
      id: 'phase-8-attempt',
      startedAt: '2026-07-28T10:30:00.000Z',
    });

    expect(restoreAttempt(JSON.stringify(legacyAttempt))).toMatchObject({
      id: 'phase-8-attempt',
      activeDeploymentRunId: null,
      deploymentRuns: {},
      lastShippingAddress: null,
      shipments: {},
    });
  });

  it.each([
    'not json',
    '[]',
    '{"id":"partial"}',
    '{"id":"x","startedAt":"not-a-date","supersededById":null,"ticketOverlays":{},"grades":{}}',
  ])('returns null rather than throwing for invalid input: %s', (json) => {
    expect(() => restoreAttempt(json)).not.toThrow();
    expect(restoreAttempt(json)).toBeNull();
  });
});
