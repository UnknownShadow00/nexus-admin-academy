import type { RequesterDevice } from '@service-desk/shared';
import { Badge, Card, CardHeader } from '@service-desk/ui';
import {
  IconDeviceDesktop,
  IconDeviceLaptop,
  IconDeviceMobile,
  IconHeadphones,
} from '@tabler/icons-react';

const DEVICE_ICONS = {
  desktop: IconDeviceDesktop,
  laptop: IconDeviceLaptop,
  mobile: IconDeviceMobile,
  peripheral: IconHeadphones,
} as const;

const STATE_VARIANTS = {
  active: 'success',
  attention: 'amber',
  offline: 'default',
} as const;

export function RelatedDevicePanel({ device }: { device: RequesterDevice }) {
  const DeviceIcon = DEVICE_ICONS[device.kind];

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <DeviceIcon aria-hidden="true" className="h-5 w-5 text-sky-400" />
            Related device
          </span>
        }
      />
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-mono text-sm font-semibold text-zinc-100">
              {device.assetTag}
            </p>
            <p className="mt-1 truncate text-sm text-zinc-300">
              {device.deviceName}
            </p>
          </div>
          <Badge variant={STATE_VARIANTS[device.state]}>{device.state}</Badge>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div>
            <dt className="font-bold uppercase tracking-wide text-zinc-500">
              Type
            </dt>
            <dd className="mt-1 capitalize text-zinc-300">{device.kind}</dd>
          </div>
          <div>
            <dt className="font-bold uppercase tracking-wide text-zinc-500">
              Platform
            </dt>
            <dd className="mt-1 text-zinc-300">{device.operatingSystem}</dd>
          </div>
        </dl>
        <p className="mt-4 border-t border-zinc-800 pt-3 text-xs leading-relaxed text-zinc-500">
          Local fixture record only; Directory and Asset Management remain
          placeholder workspaces.
        </p>
      </div>
    </Card>
  );
}
