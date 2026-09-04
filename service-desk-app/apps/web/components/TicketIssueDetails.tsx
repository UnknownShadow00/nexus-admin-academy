import type { TicketDescription } from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import { IconFileDescription } from '@tabler/icons-react';

export function TicketIssueDetails({
  description,
}: {
  description: TicketDescription;
}) {
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <IconFileDescription
              aria-hidden="true"
              className="h-5 w-5 text-accent"
            />
            Issue details
          </span>
        }
      />
      <div className="space-y-5 p-4 text-sm leading-relaxed sm:p-5">
        <section>
          <h2 className="text-xs font-extrabold uppercase tracking-wide text-text-muted">
            Reported by
          </h2>
          <p className="mt-1 text-text">{description.reportedByLine}</p>
        </section>
        <section>
          <h2 className="text-xs font-extrabold uppercase tracking-wide text-text-muted">
            Issue description
          </h2>
          <p className="mt-1 text-text">{description.issue}</p>
        </section>
        <section>
          <h2 className="text-xs font-extrabold uppercase tracking-wide text-text-muted">
            Troubleshooting already tried
          </h2>
          <ul className="mt-2 space-y-2 text-text">
            {description.troubleshooting.map((step) => (
              <li className="flex gap-2" key={step}>
                <span aria-hidden="true" className="text-accent">
                  —
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-sm border border-warning/20 bg-warning/5 p-3">
          <h2 className="text-xs font-extrabold uppercase tracking-wide text-warning">
            Business impact
          </h2>
          <p className="mt-1 text-text">{description.businessImpact}</p>
        </section>
      </div>
    </Card>
  );
}
