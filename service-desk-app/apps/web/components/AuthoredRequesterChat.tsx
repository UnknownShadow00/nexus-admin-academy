'use client';

import { REALISM_FIXTURES } from '@service-desk/shared';
import { Button } from '@service-desk/ui';
import {
  useRemoteDesktopSession,
  useTicketSession,
} from './TicketSessionProvider';

/** Known question identifiers use the same scoped, replayed action transport as
 * the workstation. Free-form chat is never promoted to diagnostic evidence. */
export function AuthoredRequesterChat({ ticketId }: { ticketId: string }) {
  const remote = useRemoteDesktopSession();
  const { getTicket } = useTicketSession();
  const fixture = REALISM_FIXTURES[ticketId];
  if (!fixture?.questions) return null;
  const workstation = remote.workstations.find(
    (item) => item.assetTag === fixture.assetTag,
  );
  const history =
    workstation?.terminalHistory.filter((entry) =>
      fixture.questions!.some((question) => question.command === entry.command),
    ) ?? [];
  return (
    <section className="space-y-4 p-5" aria-label="Requester conversation">
      <h2 className="text-lg font-bold">
        Company Chat — {getTicket(ticketId)?.requester.name}
      </h2>
      <p>
        Ask the requester about this ticket. Replies are authored for this
        attempt.
      </p>
      <div className="flex flex-wrap gap-2">
        {fixture.questions.map((question) => (
          <Button
            key={question.id}
            onClick={() =>
              remote.runTerminalCommand(fixture.assetTag, question.command)
            }
          >
            {question.label}
          </Button>
        ))}
      </div>
      <div role="log" className="space-y-3">
        {history.map((entry, index) => (
          <div key={index}>
            <p className="font-semibold">
              You:{' '}
              {
                fixture.questions!.find(
                  (question) => question.command === entry.command,
                )?.label
              }
            </p>
            <p>{entry.output.join(' ')}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
