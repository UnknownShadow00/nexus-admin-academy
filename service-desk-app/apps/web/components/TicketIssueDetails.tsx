import type { TicketDescription } from '@service-desk/shared';
import { IconFileDescription } from '@tabler/icons-react';

export function TicketIssueDetails({
  description,
}: {
  description: TicketDescription;
}) {
  return (
    <div className="border-t border-border pt-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-text">
        <IconFileDescription
          aria-hidden="true"
          className="h-5 w-5 text-accent"
        />
        Full report
      </h3>
      <div className="mt-4 grid gap-5 text-sm leading-relaxed sm:grid-cols-2">
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Reported by
          </h4>
          <p className="mt-1 text-text">{description.reportedByLine}</p>
        </section>
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Issue description
          </h4>
          <p className="mt-1 text-text">{description.issue}</p>
        </section>
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Troubleshooting already tried
          </h4>
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
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Business impact
          </h4>
          <p className="mt-1 text-text">{description.businessImpact}</p>
        </section>
      </div>
    </div>
  );
}
