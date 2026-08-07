import type { Requester } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import {
  IconBuilding,
  IconMail,
  IconMapPin,
  IconPhone,
  IconUser,
} from '@tabler/icons-react';

const REQUESTER_FIELDS = [
  { icon: IconBuilding, key: 'department', label: 'Department' },
  { icon: IconMapPin, key: 'location', label: 'Location' },
  { icon: IconMail, key: 'email', label: 'Email' },
  { icon: IconPhone, key: 'contact', label: 'Contact' },
] as const;

export function RequesterCard({ requester }: { requester: Requester }) {
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <IconUser aria-hidden="true" className="h-5 w-5 text-sky-400" />
            Requester
          </span>
        }
      />
      <div className="p-4">
        <p className="text-base font-bold text-zinc-100">{requester.name}</p>
        <dl className="mt-4 space-y-3">
          {REQUESTER_FIELDS.map(({ icon: Icon, key, label }) => (
            <div className="flex min-w-0 items-start gap-2" key={key}>
              <Icon
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500"
              />
              <div className="min-w-0">
                <dt className="text-[11px] font-bold uppercase tracking-wide text-zinc-500">
                  {label}
                </dt>
                <dd className="break-words text-sm text-zinc-300">
                  {requester[key]}
                </dd>
              </div>
            </div>
          ))}
        </dl>
      </div>
    </Card>
  );
}
