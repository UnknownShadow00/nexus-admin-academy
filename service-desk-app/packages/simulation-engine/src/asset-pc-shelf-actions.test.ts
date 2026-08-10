import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  AssetStatus,
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';

const ACTOR_ID = 'student-1';
const DIRECTORY_ASSET_TAG = 'NX-4831';
const SHELF_ASSET_TAG = 'SD9099';

function apply(
  attempt: ReturnType<typeof createAttempt>,
  action: SimulationAction,
) {
  return applyAction(attempt, ACTOR_ID, action);
}

describe('asset actions', () => {
  it('unassigns an inventory asset and rejects unassigning it twice', () => {
    const unassigned = apply(createAttempt(), {
      type: 'asset.unassign',
      payload: { assetTag: DIRECTORY_ASSET_TAG },
    });
    const rejected = apply(unassigned.attempt, {
      type: 'asset.unassign',
      payload: { assetTag: DIRECTORY_ASSET_TAG },
    });

    expect(unassigned.event.success).toBe(true);
    expect(
      unassigned.attempt.assetOverlays[DIRECTORY_ASSET_TAG]
        ?.assignedDirectoryUserId,
    ).toBeNull();
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already unassigned');
    expect(
      rejected.attempt.assetOverlays[DIRECTORY_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('assigns an unassigned asset and rejects the same assignment', () => {
    const unassigned = apply(createAttempt(), {
      type: 'asset.unassign',
      payload: { assetTag: DIRECTORY_ASSET_TAG },
    });
    const assigned = apply(unassigned.attempt, {
      type: 'asset.assign',
      payload: {
        assetTag: DIRECTORY_ASSET_TAG,
        directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
      },
    });
    const rejected = apply(assigned.attempt, {
      type: 'asset.assign',
      payload: {
        assetTag: DIRECTORY_ASSET_TAG,
        directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
      },
    });

    expect(assigned.event.success).toBe(true);
    expect(
      assigned.attempt.assetOverlays[DIRECTORY_ASSET_TAG]
        ?.assignedDirectoryUserId,
    ).toBe(SLOANE_RIVERA_DIRECTORY_USER_ID);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already assigned to');
    expect(
      rejected.attempt.assetOverlays[DIRECTORY_ASSET_TAG]?.events,
    ).toHaveLength(3);
  });

  it('changes a real asset status and rejects an unchanged status', () => {
    const changed = apply(createAttempt(), {
      type: 'asset.change_status',
      payload: {
        assetTag: DIRECTORY_ASSET_TAG,
        status: AssetStatus.Lost,
      },
    });
    const rejected = apply(changed.attempt, {
      type: 'asset.change_status',
      payload: {
        assetTag: DIRECTORY_ASSET_TAG,
        status: AssetStatus.Lost,
      },
    });

    expect(changed.event.success).toBe(true);
    expect(changed.attempt.assetOverlays[DIRECTORY_ASSET_TAG]?.status).toBe(
      AssetStatus.Lost,
    );
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already marked');
    expect(
      rejected.attempt.assetOverlays[DIRECTORY_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('records an auditable headset isolation check without changing inventory state', () => {
    const result = apply(createAttempt(), {
      type: 'asset.record_isolation',
      payload: {
        assetTag: 'NX-9052',
        test: 'affected-headset-known-good-workstation',
      },
    });

    expect(result.event.success).toBe(true);
    expect(result.attempt.assetOverlays['NX-9052']?.events).toHaveLength(1);
    expect(result.attempt.assetOverlays['NX-9052']?.status).toBeDefined();
  });

  it('keeps an SD shelf computer and Asset Management assignment in sync', () => {
    const assigned = apply(createAttempt(), {
      type: 'asset.assign',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      },
    });

    expect(assigned.event.success).toBe(true);
    expect(
      assigned.attempt.assetOverlays[SHELF_ASSET_TAG]?.assignedDirectoryUserId,
    ).toBe(AVERY_BROOKS_DIRECTORY_USER_ID);
    expect(assigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.deviceState).toBe(
      PcShelfDeviceState.Assigned,
    );
    expect(
      assigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]
        ?.assignedDirectoryUserId,
    ).toBe(AVERY_BROOKS_DIRECTORY_USER_ID);
  });
});

describe('PC Shelf actions', () => {
  it('adds a catalog computer and rejects adding it twice', () => {
    const added = apply(createAttempt(), {
      type: 'pc_shelf.add',
      payload: { assetTag: 'SD6893' },
    });
    const rejected = apply(added.attempt, {
      type: 'pc_shelf.add',
      payload: { assetTag: 'SD6893' },
    });

    expect(added.event.success).toBe(true);
    expect(added.attempt.pcShelfOverlays.SD6893?.present).toBe(true);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already on');
    expect(rejected.attempt.pcShelfOverlays.SD6893?.events).toHaveLength(2);
  });

  it('removes an unassigned computer and rejects removing it twice', () => {
    const removed = apply(createAttempt(), {
      type: 'pc_shelf.remove',
      payload: { assetTag: SHELF_ASSET_TAG },
    });
    const rejected = apply(removed.attempt, {
      type: 'pc_shelf.remove',
      payload: { assetTag: SHELF_ASSET_TAG },
    });

    expect(removed.event.success).toBe(true);
    expect(removed.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.present).toBe(
      false,
    );
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('not currently');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('changes network status and rejects the same status', () => {
    const changed = apply(createAttempt(), {
      type: 'pc_shelf.change_network_status',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        networkStatus: PcShelfNetworkStatus.Offline,
      },
    });
    const rejected = apply(changed.attempt, {
      type: 'pc_shelf.change_network_status',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        networkStatus: PcShelfNetworkStatus.Offline,
      },
    });

    expect(changed.event.success).toBe(true);
    expect(
      changed.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.networkStatus,
    ).toBe(PcShelfNetworkStatus.Offline);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already offline');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('changes device state and rejects the same state', () => {
    const changed = apply(createAttempt(), {
      type: 'pc_shelf.change_device_state',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        deviceState: PcShelfDeviceState.Retired,
      },
    });
    const rejected = apply(changed.attempt, {
      type: 'pc_shelf.change_device_state',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        deviceState: PcShelfDeviceState.Retired,
      },
    });

    expect(changed.event.success).toBe(true);
    expect(changed.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.deviceState).toBe(
      PcShelfDeviceState.Retired,
    );
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already retired');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('assigns a computer and rejects the same employee assignment', () => {
    const assigned = apply(createAttempt(), {
      type: 'pc_shelf.assign',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      },
    });
    const rejected = apply(assigned.attempt, {
      type: 'pc_shelf.assign',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      },
    });

    expect(assigned.event.success).toBe(true);
    expect(
      assigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]
        ?.assignedDirectoryUserId,
    ).toBe(AVERY_BROOKS_DIRECTORY_USER_ID);
    expect(assigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.deviceState).toBe(
      PcShelfDeviceState.Assigned,
    );
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already assigned to');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });

  it('unassigns a computer and rejects unassigning it twice', () => {
    const assigned = apply(createAttempt(), {
      type: 'pc_shelf.assign',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      },
    });
    const unassigned = apply(assigned.attempt, {
      type: 'pc_shelf.unassign',
      payload: { assetTag: SHELF_ASSET_TAG },
    });
    const rejected = apply(unassigned.attempt, {
      type: 'pc_shelf.unassign',
      payload: { assetTag: SHELF_ASSET_TAG },
    });

    expect(unassigned.event.success).toBe(true);
    expect(
      unassigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]
        ?.assignedDirectoryUserId,
    ).toBeNull();
    expect(
      unassigned.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.deviceState,
    ).toBe(PcShelfDeviceState.OnShelf);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already unassigned');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(3);
  });

  it('rejects removing an assigned computer and records one event', () => {
    const assigned = apply(createAttempt(), {
      type: 'pc_shelf.assign',
      payload: {
        assetTag: SHELF_ASSET_TAG,
        directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      },
    });
    const rejected = apply(assigned.attempt, {
      type: 'pc_shelf.remove',
      payload: { assetTag: SHELF_ASSET_TAG },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('assigned computer');
    expect(
      rejected.attempt.pcShelfOverlays[SHELF_ASSET_TAG]?.events,
    ).toHaveLength(2);
  });
});
