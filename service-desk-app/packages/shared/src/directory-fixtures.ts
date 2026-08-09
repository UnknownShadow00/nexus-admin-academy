import { AssetStatus } from './enums';

export const DIRECTORY_GROUP_NAMES = [
  'All Staff',
  'Finance Operations Updates',
  'Facilities Team',
  'Facilities Calendar',
  'Distribution Dispatch',
  'Customer Care',
  'Product Design Review',
] as const;

export type DirectoryGroupName = (typeof DIRECTORY_GROUP_NAMES)[number];

export interface DirectoryDevice {
  assetTag: string;
  deviceType: string;
  location: string;
  serialNumber: string;
  status: AssetStatus;
}

export interface DirectoryLicense {
  productName: string;
  assigned: boolean;
}

export interface DirectoryUserTemplate {
  id: string;
  fullName: string;
  username: string;
  department: string;
  jobTitle: string;
  assetTag: string;
  locked: boolean;
  disabled: boolean;
  mfaEnrolled: boolean;
  groups: readonly DirectoryGroupName[];
  devices: readonly DirectoryDevice[];
  licenses: readonly DirectoryLicense[];
}

export interface DirectoryGroupTemplate {
  id: string;
  name: DirectoryGroupName;
  memberUserIds: readonly string[];
}

interface DirectoryUserSeed {
  id: string;
  fullName: string;
  department: string;
  jobTitle: string;
  assetTag: string;
  groups: readonly DirectoryGroupName[];
  locked?: boolean;
  disabled?: boolean;
  mfaEnrolled?: boolean;
  deviceType?: string;
  deviceStatus?: AssetStatus;
}

const DEVICE_LOCATIONS = [
  'HQ - Floor 2',
  'HQ - Floor 4',
  'Remote',
  'Warehouse A',
  'Distribution Center',
] as const;

function assetNumber(assetTag: string) {
  return [...assetTag].reduce(
    (total, character) => total + character.charCodeAt(0),
    0,
  );
}

function deviceLocation(assetTag: string) {
  return DEVICE_LOCATIONS[
    assetNumber(assetTag) % DEVICE_LOCATIONS.length
  ] as (typeof DEVICE_LOCATIONS)[number];
}

function deviceSerialNumber(assetTag: string) {
  const compactTag = assetTag.replace(/[^A-Z0-9]/gi, '').toUpperCase();
  return `NXS-${compactTag}-${String(assetNumber(assetTag) * 37).padStart(5, '0')}`;
}

function deriveUsername(fullName: string) {
  const nameParts = fullName.toLowerCase().split(' ');
  return `${nameParts[0]?.[0] ?? ''}${nameParts.at(-1) ?? ''}`.replace(
    /[^a-z0-9]/g,
    '',
  );
}

function departmentLicense(department: string): DirectoryLicense {
  const productByDepartment: Readonly<Record<string, string>> = {
    'Customer Care': 'Beacon Contact Console',
    Distribution: 'Routeboard Dispatch',
    Facilities: 'Siteplan Workspace',
    'Finance Operations': 'LedgerView Analytics',
    'People Operations': 'Harbor People Hub',
    'Product Design': 'CanvasForge Studio',
    'Security Operations': 'Sentinel Case Desk',
    'Technology Services': 'Orbit Admin Console',
  };

  return {
    productName: productByDepartment[department] ?? 'Northstar Office Suite',
    assigned: true,
  };
}

function createDirectoryUser(seed: DirectoryUserSeed): DirectoryUserTemplate {
  return {
    ...seed,
    username: deriveUsername(seed.fullName),
    locked: seed.locked ?? false,
    disabled: seed.disabled ?? false,
    mfaEnrolled: seed.mfaEnrolled ?? true,
    devices: [
      {
        assetTag: seed.assetTag,
        deviceType: seed.deviceType ?? 'laptop',
        location: deviceLocation(seed.assetTag),
        serialNumber: deviceSerialNumber(seed.assetTag),
        status: seed.deviceStatus ?? AssetStatus.Deployed,
      },
    ],
    licenses: [
      { productName: 'Northstar Office Suite', assigned: true },
      { productName: 'Relay Meet', assigned: true },
      departmentLicense(seed.department),
    ],
  };
}

export const AVERY_BROOKS_DIRECTORY_USER_ID = 'directory-user-avery-brooks';
export const SLOANE_RIVERA_DIRECTORY_USER_ID = 'directory-user-sloane-rivera';
export const FACILITIES_CALENDAR_GROUP = 'Facilities Calendar';

export const DIRECTORY_USER_FIXTURES: readonly DirectoryUserTemplate[] = [
  createDirectoryUser({
    id: AVERY_BROOKS_DIRECTORY_USER_ID,
    fullName: 'Avery Brooks',
    department: 'Finance Operations',
    jobTitle: 'Reconciliation Analyst',
    assetTag: 'NX-4831',
    groups: ['All Staff', 'Finance Operations Updates'],
  }),
  createDirectoryUser({
    id: SLOANE_RIVERA_DIRECTORY_USER_ID,
    fullName: 'Sloane Rivera',
    department: 'Facilities',
    jobTitle: 'Facilities Coordinator',
    assetTag: 'NX-6128',
    groups: ['All Staff', 'Facilities Team', FACILITIES_CALENDAR_GROUP],
  }),
  createDirectoryUser({
    id: 'directory-user-noah-vance',
    fullName: 'Noah Vance',
    department: 'Distribution',
    jobTitle: 'Dispatch Lead',
    assetTag: 'NX-7714',
    groups: ['All Staff', 'Distribution Dispatch'],
    deviceType: 'mobile workstation',
  }),
  createDirectoryUser({
    id: 'directory-user-mina-patel',
    fullName: 'Mina Patel',
    department: 'Product Design',
    jobTitle: 'Product Designer',
    assetTag: 'NX-3560',
    groups: ['All Staff', 'Product Design Review'],
    deviceType: 'desktop',
  }),
  createDirectoryUser({
    id: 'directory-user-elliot-ward',
    fullName: 'Elliot Ward',
    department: 'Customer Care',
    jobTitle: 'Customer Advisor',
    assetTag: 'NX-9052',
    groups: ['All Staff', 'Customer Care'],
  }),
  createDirectoryUser({
    id: 'directory-user-iris-caldwell',
    fullName: 'Iris Caldwell',
    department: 'People Operations',
    jobTitle: 'Former Recruiting Partner',
    assetTag: 'NX-2014',
    groups: ['All Staff'],
    disabled: true,
    mfaEnrolled: false,
    deviceStatus: AssetStatus.Damaged,
  }),
  createDirectoryUser({
    id: 'directory-user-jules-hart',
    fullName: 'Jules Hart',
    department: 'Facilities',
    jobTitle: 'Workplace Services Lead',
    assetTag: 'NX-6240',
    groups: ['All Staff', 'Facilities Team', 'Facilities Calendar'],
  }),
  createDirectoryUser({
    id: 'directory-user-remy-chen',
    fullName: 'Remy Chen',
    department: 'Finance Operations',
    jobTitle: 'Treasury Specialist',
    assetTag: 'NX-4810',
    groups: ['All Staff', 'Finance Operations Updates'],
  }),
  createDirectoryUser({
    id: 'directory-user-lena-morrow',
    fullName: 'Lena Morrow',
    department: 'Technology Services',
    jobTitle: 'Endpoint Engineer',
    assetTag: 'NX-1042',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-omar-sayeed',
    fullName: 'Omar Sayeed',
    department: 'Security Operations',
    jobTitle: 'Security Analyst',
    assetTag: 'NX-1126',
    groups: ['All Staff'],
    locked: true,
  }),
  createDirectoryUser({
    id: 'directory-user-nia-carver',
    fullName: 'Nia Carver',
    department: 'Customer Care',
    jobTitle: 'Quality Coach',
    assetTag: 'NX-9088',
    groups: ['All Staff', 'Customer Care'],
  }),
  createDirectoryUser({
    id: 'directory-user-theo-kim',
    fullName: 'Theo Kim',
    department: 'Product Design',
    jobTitle: 'Design Researcher',
    assetTag: 'NX-3524',
    groups: ['All Staff', 'Product Design Review'],
  }),
  createDirectoryUser({
    id: 'directory-user-carmen-doyle',
    fullName: 'Carmen Doyle',
    department: 'Distribution',
    jobTitle: 'Inventory Planner',
    assetTag: 'NX-7738',
    groups: ['All Staff', 'Distribution Dispatch'],
  }),
  createDirectoryUser({
    id: 'directory-user-dev-shah',
    fullName: 'Dev Shah',
    department: 'Technology Services',
    jobTitle: 'Service Desk Analyst',
    assetTag: 'NX-1093',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-piper-frost',
    fullName: 'Piper Frost',
    department: 'Facilities',
    jobTitle: 'Space Planning Analyst',
    assetTag: 'NX-6287',
    groups: ['All Staff', 'Facilities Team', 'Facilities Calendar'],
  }),
  createDirectoryUser({
    id: 'directory-user-mateo-rusk',
    fullName: 'Mateo Rusk',
    department: 'Finance Operations',
    jobTitle: 'Accounts Specialist',
    assetTag: 'NX-4866',
    groups: ['All Staff', 'Finance Operations Updates'],
  }),
  createDirectoryUser({
    id: 'directory-user-wren-bishop',
    fullName: 'Wren Bishop',
    department: 'People Operations',
    jobTitle: 'Learning Coordinator',
    assetTag: 'NX-2049',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-kenji-ross',
    fullName: 'Kenji Ross',
    department: 'Security Operations',
    jobTitle: 'Risk Coordinator',
    assetTag: 'NX-1175',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-alina-greer',
    fullName: 'Alina Greer',
    department: 'Customer Care',
    jobTitle: 'Escalations Advisor',
    assetTag: 'NX-9120',
    groups: ['All Staff', 'Customer Care'],
  }),
  createDirectoryUser({
    id: 'directory-user-felix-nolan',
    fullName: 'Felix Nolan',
    department: 'Product Design',
    jobTitle: 'Prototype Engineer',
    assetTag: 'NX-3591',
    groups: ['All Staff', 'Product Design Review'],
    deviceType: 'desktop',
  }),
  createDirectoryUser({
    id: 'directory-user-talia-woods',
    fullName: 'Talia Woods',
    department: 'Distribution',
    jobTitle: 'Logistics Coordinator',
    assetTag: 'NX-7782',
    groups: ['All Staff', 'Distribution Dispatch'],
  }),
  createDirectoryUser({
    id: 'directory-user-hugo-bell',
    fullName: 'Hugo Bell',
    department: 'Technology Services',
    jobTitle: 'Systems Administrator',
    assetTag: 'NX-1211',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-zara-cole',
    fullName: 'Zara Cole',
    department: 'Facilities',
    jobTitle: 'Maintenance Planner',
    assetTag: 'NX-6332',
    groups: ['All Staff', 'Facilities Team', 'Facilities Calendar'],
  }),
  createDirectoryUser({
    id: 'directory-user-evan-laird',
    fullName: 'Evan Laird',
    department: 'Finance Operations',
    jobTitle: 'Reporting Analyst',
    assetTag: 'NX-4897',
    groups: ['All Staff', 'Finance Operations Updates'],
  }),
  createDirectoryUser({
    id: 'directory-user-briar-stone',
    fullName: 'Briar Stone',
    department: 'People Operations',
    jobTitle: 'Benefits Specialist',
    assetTag: 'NX-2091',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-amara-okafor',
    fullName: 'Amara Okafor',
    department: 'Security Operations',
    jobTitle: 'Identity Analyst',
    assetTag: 'NX-1248',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-callum-reed',
    fullName: 'Callum Reed',
    department: 'Customer Care',
    jobTitle: 'Workforce Planner',
    assetTag: 'NX-9164',
    groups: ['All Staff', 'Customer Care'],
  }),
  createDirectoryUser({
    id: 'directory-user-maya-quinn',
    fullName: 'Maya Quinn',
    department: 'Product Design',
    jobTitle: 'Content Designer',
    assetTag: 'NX-3630',
    groups: ['All Staff', 'Product Design Review'],
  }),
  createDirectoryUser({
    id: 'directory-user-ronan-clark',
    fullName: 'Ronan Clark',
    department: 'Distribution',
    jobTitle: 'Fulfillment Supervisor',
    assetTag: 'NX-7826',
    groups: ['All Staff', 'Distribution Dispatch'],
    locked: true,
  }),
  createDirectoryUser({
    id: 'directory-user-selene-price',
    fullName: 'Selene Price',
    department: 'Technology Services',
    jobTitle: 'Network Engineer',
    assetTag: 'NX-1296',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-archie-lin',
    fullName: 'Archie Lin',
    department: 'Facilities',
    jobTitle: 'Site Services Coordinator',
    assetTag: 'NX-6385',
    groups: ['All Staff', 'Facilities Team', 'Facilities Calendar'],
  }),
  createDirectoryUser({
    id: 'directory-user-dara-knox',
    fullName: 'Dara Knox',
    department: 'Finance Operations',
    jobTitle: 'Billing Coordinator',
    assetTag: 'NX-4935',
    groups: ['All Staff', 'Finance Operations Updates'],
  }),
  createDirectoryUser({
    id: 'directory-user-yara-benson',
    fullName: 'Yara Benson',
    department: 'People Operations',
    jobTitle: 'Talent Programs Partner',
    assetTag: 'NX-2137',
    groups: ['All Staff'],
  }),
  createDirectoryUser({
    id: 'directory-user-gideon-park',
    fullName: 'Gideon Park',
    department: 'Security Operations',
    jobTitle: 'Compliance Specialist',
    assetTag: 'NX-1344',
    groups: ['All Staff'],
    disabled: true,
    deviceStatus: AssetStatus.Retired,
  }),
  createDirectoryUser({
    id: 'directory-user-liv-holland',
    fullName: 'Liv Holland',
    department: 'Customer Care',
    jobTitle: 'Training Advisor',
    assetTag: 'NX-9210',
    groups: ['All Staff', 'Customer Care'],
    mfaEnrolled: false,
  }),
  createDirectoryUser({
    id: 'directory-user-samir-wells',
    fullName: 'Samir Wells',
    department: 'Product Design',
    jobTitle: 'Design Operations Lead',
    assetTag: 'NX-3672',
    groups: ['All Staff', 'Product Design Review'],
  }),
] as const;

export const DIRECTORY_GROUP_FIXTURES: readonly DirectoryGroupTemplate[] =
  DIRECTORY_GROUP_NAMES.map((name) => ({
    id: `directory-group-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    name,
    memberUserIds: DIRECTORY_USER_FIXTURES.filter((user) =>
      user.groups.includes(name),
    ).map((user) => user.id),
  }));

export function getDirectoryUserById(directoryUserId: string) {
  return DIRECTORY_USER_FIXTURES.find((user) => user.id === directoryUserId);
}
