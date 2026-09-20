import type { ActivityEvent } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import { IconActivity, IconCircleCheck } from '@tabler/icons-react';

import { formatActivityTimestamp } from './ticket-labels';

const DOT_CLASSES: Record<NonNullable<ActivityEvent['tone']>, string> = {
  default: 'text-text-muted',
  info: 'text-accent',
  success: 'text-success',
  warning: 'text-warning',
};

export function ActivityTimeline({
  events,
}: {
  events: readonly ActivityEvent[];
}) {
  return (
    <Card>
      <CardHeader
        meta={`${events.length} ${events.length === 1 ? 'event' : 'events'}`}
        title={
          <span className="flex items-center gap-2">
            <IconActivity aria-hidden="true" className="h-5 w-5 text-accent" />
            Activity
          </span>
        }
      />
      <ol className="divide-y divide-border">
        {[...events].reverse().map((event) => (
          <li className="flex gap-3 px-4 py-3 sm:px-5" key={event.id}>
            <IconCircleCheck
              aria-hidden="true"
              className={`mt-0.5 h-4 w-4 shrink-0 ${
                DOT_CLASSES[event.tone ?? 'default']
              }`}
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
                <p className="text-sm font-semibold text-text">
                  {event.label}
                </p>
                <time
                  className="shrink-0 text-[11px] text-text-muted"
                  dateTime={event.timestamp}
                >
                  {formatActivityTimestamp(event.timestamp)}
                </time>
              </div>
              {event.detail ? (
                <p className="mt-1 text-xs leading-relaxed text-text-muted">
                  {event.detail}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
