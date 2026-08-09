import { DIRECTORY_USER_FIXTURES } from './directory-fixtures';

export const SHIPPING_DEPARTMENTS = [
  'IT Department',
  'Accounting',
  'Customer Support',
  'Design',
  'Engineering',
  'Executive',
  'Facilities',
  'Finance',
  'HR',
  'Legal',
  'Marketing',
  'Operations',
  'Sales',
] as const;

export type ShippingDepartment = (typeof SHIPPING_DEPARTMENTS)[number];

export const SHIPPING_EQUIPMENT = [
  'HDMI Cable',
  'DisplayPort Cable',
  'USB-C Cable',
  'Laptop Charger',
  'Headset',
  'Desktop Power Cable',
  'Computer',
  'Monitor',
] as const;

export type ShippingEquipmentName = (typeof SHIPPING_EQUIPMENT)[number];

export const SHIPPING_SPEEDS = [
  { id: 'standard', label: 'Standard', detail: '5-7 days' },
  { id: 'express', label: 'Express', detail: '2 days' },
  { id: 'priority', label: 'Priority', detail: 'Same day' },
  { id: 'rush', label: 'Rush Priority', detail: 'Instant' },
] as const;

export type ShippingSpeed = (typeof SHIPPING_SPEEDS)[number]['id'];

export interface ShippingAddressFixture {
  street: string;
  city: string;
  state: string;
  postalCode: string;
}

const SHIPPING_CITIES = [
  ['Seattle', 'WA', '98101'],
  ['Portland', 'OR', '97205'],
  ['Denver', 'CO', '80202'],
  ['Austin', 'TX', '78701'],
  ['Chicago', 'IL', '60601'],
  ['Boston', 'MA', '02108'],
] as const;

export const DIRECTORY_SHIPPING_ADDRESSES: Readonly<
  Record<string, ShippingAddressFixture>
> = Object.fromEntries(
  DIRECTORY_USER_FIXTURES.map((user, index) => {
    const city = SHIPPING_CITIES[index % SHIPPING_CITIES.length];
    return [
      user.id,
      {
        street: `${120 + index * 17} ${['Cedar', 'Pine', 'Lake', 'Market'][index % 4]} Street`,
        city: city?.[0] ?? 'Seattle',
        state: city?.[1] ?? 'WA',
        postalCode: city?.[2] ?? '98101',
      },
    ];
  }),
);

export function getDirectoryShippingAddress(directoryUserId: string) {
  return DIRECTORY_SHIPPING_ADDRESSES[directoryUserId];
}
