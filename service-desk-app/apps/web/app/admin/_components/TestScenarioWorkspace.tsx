'use client';

import {
  DIRECTORY_GROUP_NAMES,
  DIRECTORY_USER_FIXTURES,
  getScenario,
  getTestStudent,
  listScenarios,
  type ScenarioVersion,
} from '@service-desk/shared';
import {
  applyAction,
  applyScenarioTicketAction,
  evaluateScenarioObjectives,
  scenarioTicketId,
  type ActionEvent,
  type Attempt,
  type DirectorySimulationAction,
  type TicketSimulationAction,
} from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Select,
  Textarea,
} from '@service-desk/ui';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { loadTestAttempt, saveTestAttempt } from '../_lib/test-attempt';

const ACTOR_ID = 'admin-test-student';

export function TestScenarioWorkspace({
  scenarioId,
  slotId,
}: {
  scenarioId: string;
  slotId: string;
}) {
  const [version, setVersion] = useState<ScenarioVersion | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [feedback, setFeedback] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  const [verifiedResolved, setVerifiedResolved] = useState(true);
  const [directoryUserId, setDirectoryUserId] = useState(
    DIRECTORY_USER_FIXTURES[0]?.id ?? '',
  );
  const [directoryGroup, setDirectoryGroup] = useState<string>(
    DIRECTORY_GROUP_NAMES[0] ?? '',
  );

  useEffect(() => {
    const record = getScenario(scenarioId);
    const slot = getTestStudent(slotId);
    if (
      !record ||
      !slot?.assignedScenarioIds.includes(scenarioId) ||
      !record.template.activeVersionId
    ) {
      return;
    }
    const active = record.versions.find(
      (candidate) => candidate.id === record.template.activeVersionId,
    );
    if (!active) {
      return;
    }
    const assignedVersions = listScenarios().flatMap((candidate) => {
      const candidateVersion = candidate.versions.find(
        (item) => item.id === candidate.template.activeVersionId,
      );
      return candidateVersion &&
        slot.assignedScenarioIds.includes(candidate.template.id)
        ? [candidateVersion]
        : [];
    });
    setVersion(active);
    setAttempt(loadTestAttempt(slotId, assignedVersions));
    const firstRelevantUser =
      Object.keys(active.initialWorldState.directoryOverlaySeeds)[0] ??
      active.objectives.find(
        (objective) =>
          typeof objective.predicateParams.directoryUserId === 'string',
      )?.predicateParams.directoryUserId;
    if (typeof firstRelevantUser === 'string') {
      setDirectoryUserId(firstRelevantUser);
    }
  }, [scenarioId, slotId]);

  const evaluation = useMemo(
    () =>
      attempt && version ? evaluateScenarioObjectives(attempt, version) : null,
    [attempt, version],
  );

  if (!attempt || !version) {
    return (
      <div className="space-y-3">
        <p className="text-zinc-400">
          This published scenario is not assigned to this test student.
        </p>
        <Link
          className="text-sky-300 hover:underline"
          href={`/admin/test-students/${slotId}`}
        >
          Return to the slot
        </Link>
      </div>
    );
  }

  const ticketId = scenarioTicketId(version);
  const overlay = attempt.ticketOverlays[ticketId];
  const resolved = overlay?.closure?.verifiedResolved === true;

  function commit(next: Attempt, event: ActionEvent) {
    setAttempt(next);
    saveTestAttempt(slotId, next);
    setFeedback(
      event.success
        ? `${event.type} recorded.`
        : `${event.type} rejected: ${event.rejectReason}`,
    );
  }

  function ticket(action: TicketSimulationAction) {
    const result = applyScenarioTicketAction(
      attempt!,
      ACTOR_ID,
      ticketId,
      action,
    );
    commit(result.attempt, result.event);
  }

  function directory(action: DirectorySimulationAction) {
    const result = applyAction(attempt!, ACTOR_ID, action);
    commit(result.attempt, result.event);
  }

  const currentDirectoryOverlay = attempt.directoryOverlays[directoryUserId];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link
            className="text-sm font-bold text-sky-300 hover:underline"
            href={`/admin/test-students/${slotId}`}
          >
            ← Test student queue
          </Link>
          <h1 className="mt-2 text-2xl font-black">
            {version.description.issue}
          </h1>
          <div className="mt-2 flex gap-2">
            <Badge variant={resolved ? 'success' : 'amber'}>
              {resolved ? 'Resolved' : (overlay?.status ?? 'Open')}
            </Badge>
            <Badge>{version.difficulty}</Badge>
            <Badge>{version.pointValue} points</Badge>
          </div>
        </div>
        {!resolved ? (
          <Button
            onClick={() =>
              ticket({
                payload: { ticketId },
                type: 'ticket.assign',
              })
            }
            variant="soft"
          >
            Assign to me
          </Button>
        ) : null}
      </div>

      {feedback ? (
        <p className="rounded-sm border border-sky-400/30 bg-sky-400/10 p-3 text-sm text-sky-200">
          {feedback}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Ticket details" />
            <div className="space-y-5 p-4">
              <p>{version.description.issue}</p>
              <div>
                <h2 className="text-xs font-bold uppercase text-zinc-500">
                  Troubleshooting
                </h2>
                <ul className="mt-2 list-inside list-disc text-sm text-zinc-300">
                  {version.description.troubleshooting.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-sm border border-amber-400/20 bg-amber-400/5 p-3">
                <h2 className="text-xs font-bold uppercase text-amber-300">
                  Business impact
                </h2>
                <p className="mt-1 text-sm">
                  {version.description.businessImpact}
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Directory actions" />
            <div className="space-y-4 p-4">
              <div className="grid gap-2 md:grid-cols-2">
                <Select
                  aria-label="Directory user"
                  onChange={(event) => setDirectoryUserId(event.target.value)}
                  value={directoryUserId}
                >
                  {DIRECTORY_USER_FIXTURES.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.fullName}
                    </option>
                  ))}
                </Select>
                <Select
                  aria-label="Directory group"
                  onChange={(event) => setDirectoryGroup(event.target.value)}
                  value={directoryGroup}
                >
                  {DIRECTORY_GROUP_NAMES.map((group) => (
                    <option key={group}>{group}</option>
                  ))}
                </Select>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() =>
                    directory({
                      payload: { directoryUserId },
                      type: 'directory.unlock_account',
                    })
                  }
                >
                  Unlock
                </Button>
                <Button
                  onClick={() =>
                    directory({
                      payload: { directoryUserId },
                      type: 'directory.enable_account',
                    })
                  }
                >
                  Enable
                </Button>
                <Button
                  onClick={() =>
                    directory({
                      payload: { directoryUserId },
                      type: 'directory.disable_account',
                    })
                  }
                >
                  Disable
                </Button>
                <Button
                  onClick={() =>
                    directory({
                      payload: { directoryUserId },
                      type: 'directory.reset_mfa',
                    })
                  }
                >
                  Reset MFA
                </Button>
                <Button
                  onClick={() =>
                    directory({
                      payload: {
                        add: [directoryGroup],
                        directoryUserId,
                        remove: [],
                      },
                      type: 'directory.update_groups',
                    })
                  }
                >
                  Add group
                </Button>
                <Button
                  onClick={() =>
                    directory({
                      payload: {
                        add: [],
                        directoryUserId,
                        remove: [directoryGroup],
                      },
                      type: 'directory.update_groups',
                    })
                  }
                >
                  Remove group
                </Button>
              </div>
              {currentDirectoryOverlay ? (
                <pre className="overflow-auto rounded-sm bg-zinc-950 p-3 text-xs text-zinc-400">
                  {JSON.stringify(
                    {
                      disabled: currentDirectoryOverlay.disabled,
                      groupChanges: currentDirectoryOverlay.groupChanges,
                      locked: currentDirectoryOverlay.locked,
                      mfaEnrolled: currentDirectoryOverlay.mfaEnrolled,
                    },
                    null,
                    2,
                  )}
                </pre>
              ) : null}
            </div>
          </Card>

          <Card>
            <CardHeader title="Resolve scenario ticket" />
            <div className="space-y-3 p-4">
              <Textarea
                aria-label="Resolution note"
                onChange={(event) => setResolutionNote(event.target.value)}
                placeholder="Describe the resolution and verification."
                value={resolutionNote}
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  checked={verifiedResolved}
                  onChange={(event) =>
                    setVerifiedResolved(event.target.checked)
                  }
                  type="checkbox"
                />
                Requester verified the issue is resolved
              </label>
              <Button
                disabled={Boolean(overlay?.closure)}
                onClick={() =>
                  ticket({
                    payload: {
                      resolutionNote,
                      ticketId,
                      verifiedResolved,
                    },
                    type: 'ticket.close',
                  })
                }
                variant="primary"
              >
                Close scenario ticket
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Requester" />
            <dl className="space-y-2 p-4 text-sm">
              <div>
                <dt className="text-zinc-500">Name</dt>
                <dd>{version.requester.name}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Department</dt>
                <dd>{version.requester.department}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Location</dt>
                <dd>{version.requester.location}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Device</dt>
                <dd>{version.device.deviceName}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">SLA</dt>
                <dd>{version.sla.target}</dd>
              </div>
            </dl>
          </Card>
          <Card>
            <CardHeader title="Guided hints" />
            <div className="space-y-3 p-4">
              {version.hints
                .slice(0, overlay?.hintsRevealedCount ?? 0)
                .map((hint) => (
                  <p
                    className="rounded-sm border border-zinc-800 p-3 text-sm"
                    key={hint.id}
                  >
                    {hint.order}. {hint.text}{' '}
                    <span className="text-zinc-500">
                      (-{hint.pointPenalty})
                    </span>
                  </p>
                ))}
              <Button
                disabled={
                  (overlay?.hintsRevealedCount ?? 0) >= version.hints.length
                }
                onClick={() =>
                  ticket({
                    payload: {
                      step: (overlay?.hintsRevealedCount ?? 0) + 1,
                      ticketId,
                    },
                    type: 'ticket.reveal_hint',
                  })
                }
              >
                Reveal next hint
              </Button>
            </div>
          </Card>
          {evaluation ? (
            <Card>
              <CardHeader
                meta={`${evaluation.totalScore}/${evaluation.pointsPossible}`}
                title="Live evaluation"
              />
              <div className="space-y-4 p-4 text-sm">
                {evaluation.hintPenalty > 0 ? (
                  <p className="text-amber-300">
                    Hint penalty: -{evaluation.hintPenalty} points
                  </p>
                ) : null}
                <div>
                  <h3 className="font-bold">Objectives</h3>
                  {evaluation.objectives.map((item) => (
                    <p
                      className={
                        item.passed ? 'text-emerald-400' : 'text-zinc-500'
                      }
                      key={item.id}
                    >
                      {item.passed ? '✓' : '○'} {item.description} (
                      {item.earned}/{item.points})
                    </p>
                  ))}
                </div>
                <div>
                  <h3 className="font-bold">Required actions</h3>
                  {evaluation.requiredActions.map((item) => (
                    <p key={item.id}>
                      {item.passed ? '✓' : '○'} {item.description}
                    </p>
                  ))}
                </div>
                <div>
                  <h3 className="font-bold">Forbidden actions</h3>
                  {evaluation.forbiddenActions.map((item) => (
                    <p
                      className={item.passed ? 'text-zinc-400' : 'text-red-400'}
                      key={item.id}
                    >
                      {item.passed ? '✓ no violation' : '⚠ violation'} —{' '}
                      {item.description}
                    </p>
                  ))}
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
