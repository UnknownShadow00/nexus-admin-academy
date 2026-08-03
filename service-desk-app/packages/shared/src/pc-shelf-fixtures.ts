import { PcShelfDeviceState, PcShelfNetworkStatus } from './enums';

export interface PcShelfComputerFixture {
  assetTag: string;
  cpu: string;
  deploymentMethod: string;
  deviceState: PcShelfDeviceState;
  location: string;
  networkStatus: PcShelfNetworkStatus;
  operatingSystem: string;
  ram: string;
  serialNumber: string;
  storage: string;
}

export const PC_SHELF_FIXTURES: readonly PcShelfComputerFixture[] = [
  {
    assetTag: 'SD9099',
    cpu: 'Intel Core i5-14500',
    deploymentMethod: 'Server Imaging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Shelf A',
    networkStatus: PcShelfNetworkStatus.Online,
    operatingSystem: 'Windows 11 Pro',
    ram: '16 GB DDR5',
    serialNumber: 'NXS-SD9099-24071',
    storage: '512 GB NVMe',
  },
  {
    assetTag: 'SD8765',
    cpu: 'Intel Core i7-13700',
    deploymentMethod: 'Server Imaging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Shelf A',
    networkStatus: PcShelfNetworkStatus.Offline,
    operatingSystem: 'Windows 11 Enterprise',
    ram: '32 GB DDR5',
    serialNumber: 'NXS-SD8765-23812',
    storage: '1 TB NVMe',
  },
  {
    assetTag: 'SD7654',
    cpu: 'AMD Ryzen 7 PRO 7840U',
    deploymentMethod: 'Cloud Provisioning',
    deviceState: PcShelfDeviceState.Provisioning,
    location: 'IT Staging - Bench 2',
    networkStatus: PcShelfNetworkStatus.Unregistered,
    operatingSystem: 'Windows 11 Enterprise',
    ram: '32 GB DDR5',
    serialNumber: 'NXS-SD7654-23164',
    storage: '1 TB NVMe',
  },
  {
    assetTag: 'SD6214',
    cpu: 'Intel Core i5-1345U',
    deploymentMethod: 'Server Imaging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Shelf B',
    networkStatus: PcShelfNetworkStatus.Online,
    operatingSystem: 'Windows 11 Pro',
    ram: '16 GB DDR5',
    serialNumber: 'NXS-SD6214-22405',
    storage: '512 GB NVMe',
  },
  {
    assetTag: 'SD6893',
    cpu: 'Intel Core i7-1365U',
    deploymentMethod: 'Server Imaging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Shelf B',
    networkStatus: PcShelfNetworkStatus.Offline,
    operatingSystem: 'Windows 11 Enterprise',
    ram: '32 GB DDR5',
    serialNumber: 'NXS-SD6893-22738',
    storage: '1 TB NVMe',
  },
  {
    assetTag: 'SD5482',
    cpu: 'AMD Ryzen 5 PRO 7640U',
    deploymentMethod: 'Manual Staging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Shelf C',
    networkStatus: PcShelfNetworkStatus.Unregistered,
    operatingSystem: 'Windows 11 Pro',
    ram: '16 GB DDR5',
    serialNumber: 'NXS-SD5482-21907',
    storage: '512 GB NVMe',
  },
] as const;

export const INITIAL_PC_SHELF_ASSET_TAGS = [
  'SD9099',
  'SD8765',
  'SD7654',
  'SD6214',
] as const;

export function getPcShelfFixture(assetTag: string) {
  return PC_SHELF_FIXTURES.find((fixture) => fixture.assetTag === assetTag);
}
