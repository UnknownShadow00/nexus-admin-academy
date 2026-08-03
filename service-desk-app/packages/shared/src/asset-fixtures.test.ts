import { describe, expect, it } from 'vitest';

import { DIRECTORY_USER_FIXTURES } from './directory-fixtures';
import { AssetStatus, PcShelfDeviceState, PcShelfNetworkStatus } from './enums';
import {
  INITIAL_PC_SHELF_ASSET_TAGS,
  PC_SHELF_FIXTURES,
} from './pc-shelf-fixtures';

describe('asset fixtures', () => {
  it('reuses every directory identity and NX asset tag exactly once', () => {
    const devices = DIRECTORY_USER_FIXTURES.flatMap((user) =>
      user.devices.map((device) => ({
        ...device,
        directoryUserId: user.id,
      })),
    );

    expect(devices).toHaveLength(36);
    expect(new Set(devices.map((device) => device.assetTag)).size).toBe(36);
    expect(devices.every((device) => /^NX-\d{4}$/.test(device.assetTag))).toBe(
      true,
    );
    expect(
      devices.every((device) =>
        Object.values(AssetStatus).includes(device.status),
      ),
    ).toBe(true);
    expect(new Set(devices.map((device) => device.serialNumber)).size).toBe(36);
    expect(devices.every((device) => device.location.length > 0)).toBe(true);
  });

  it('provides a distinct deterministic SD shelf catalog and four seed items', () => {
    expect(PC_SHELF_FIXTURES).toHaveLength(6);
    expect(INITIAL_PC_SHELF_ASSET_TAGS).toHaveLength(4);
    expect(
      new Set(PC_SHELF_FIXTURES.map((computer) => computer.assetTag)).size,
    ).toBe(6);
    expect(
      PC_SHELF_FIXTURES.every((computer) =>
        /^SD\d{4}$/.test(computer.assetTag),
      ),
    ).toBe(true);
    expect(
      PC_SHELF_FIXTURES.every((computer) =>
        Object.values(PcShelfNetworkStatus).includes(computer.networkStatus),
      ),
    ).toBe(true);
    expect(
      PC_SHELF_FIXTURES.every((computer) =>
        Object.values(PcShelfDeviceState).includes(computer.deviceState),
      ),
    ).toBe(true);
    expect(
      INITIAL_PC_SHELF_ASSET_TAGS.every((assetTag) =>
        PC_SHELF_FIXTURES.some((computer) => computer.assetTag === assetTag),
      ),
    ).toBe(true);
  });
});
