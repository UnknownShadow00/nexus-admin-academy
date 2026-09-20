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
            <IconUser aria-hidden="true" className="h-5 w-5 text-accent" />
            Requester
          </span>
        }
      />
      <div className="p-4">
        <p className="text-base font-bold text-text">{requester.name}</p>
        <dl className="mt-4 space-y-3">
          {REQUESTER_FIELDS.map(({ icon: Icon, key, label }) => (
            <div className="flex min-w-0 items-start gap-2" key={key}>
              <Icon
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-text-muted"
              />
              <div className="min-w-0">
                <dt className="text-[11px] font-bold uppercase tracking-wide text-text-muted">
                  {label}
                </dt>
                <dd className="break-words text-sm text-text">
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
