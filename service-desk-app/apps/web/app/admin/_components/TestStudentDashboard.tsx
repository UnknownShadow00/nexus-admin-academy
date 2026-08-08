'use client';

import {
  getTestStudent,
  setTestStudentScenarioAssignment,
  type ScenarioRecord,
  type ScenarioVersion,
  type TestStudentSlot,
} from '@service-desk/shared';
import {
  collectScenarioActionEvents,
  scenarioTicketId,
  type Attempt,
} from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Modal,
  Select,
} from '@service-desk/ui';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import {
  addScenarioToTestAttempt,
  loadTestAttempt,
  resetTestAttempt,
  saveTestAttempt,
} from '../_lib/test-attempt';
import { listServerScenarios } from '../../../lib/nexus-admin-scenario-client';

function activeVersion(record: ScenarioRecord): ScenarioVersion | undefined {
  return record.versions.find(
    (version) => version.id === record.template.activeVersionId,
  );
}

export function TestStudentDashboard({ slotId }: { slotId: string }) {
  const [slot, setSlot] = useState<TestStudentSlot | null>(null);
  const [records, setRecords] = useState<ScenarioRecord[]>([]);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [scenarioToAssign, setScenarioToAssign] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const published = useMemo(
    () => records.filter((record) => Boolean(activeVersion(record))),
    [records],
  );
  const assignedVersions = useMemo(
    () =>
      published.flatMap((record) =>
        slot?.assignedScenarioIds.includes(record.template.id)
          ? [activeVersion(record)!]
          : [],
      ),
    [published, slot],
  );

  useEffect(() => {
    const nextSlot = getTestStudent(slotId);
    setSlot(nextSlot);
    void listServerScenarios().then((nextRecords) => {
      setRecords(nextRecords);
      if (nextSlot) {
        const versions = nextRecords.flatMap((record) => {
          const version = activeVersion(record);
          return version && nextSlot.assignedScenarioIds.includes(record.template.id)
            ? [version]
            : [];
        });
        const nextAttempt = loadTestAttempt(slotId, versions);
        setAttempt(nextAttempt);
        saveTestAttempt(slotId, nextAttempt);
      }
    });
  }, [slotId]);

  if (!slot || !attempt) {
    return <p className="text-zinc-400">Loading test student slot…</p>;
  }
  const events = collectScenarioActionEvents(attempt);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-bold uppercase text-amber-400">
          Test student
        </p>
        <h1 className="text-2xl font-black">{slot.name}</h1>
      </div>
      <Card>
        <CardHeader title="Published scenario assignments" />
        <div className="space-y-4 p-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Select
              aria-label="Published scenario"
              onChange={(event) => setScenarioToAssign(event.target.value)}
              value={scenarioToAssign}
            >
              <option value="">Select published scenario</option>
              {published
                .filter(
                  (record) =>
                    !slot.assignedScenarioIds.includes(record.template.id),
                )
                .map((record) => (
                  <option key={record.template.id} value={record.template.id}>
                    {record.template.title}
                  </option>
                ))}
            </Select>
            <Button
              disabled={!scenarioToAssign}
              onClick={() => {
                const record = published.find(
                  (candidate) => candidate.template.id === scenarioToAssign,
                );
                const version = record ? activeVersion(record) : undefined;
                const next = setTestStudentScenarioAssignment(
                  slot.id,
                  scenarioToAssign,
                  true,
                );
                setSlot(next);
                if (version) {
                  setAttempt(
                    addScenarioToTestAttempt(slot.id, attempt, version),
                  );
                }
                setScenarioToAssign('');
              }}
              variant="primary"
            >
              Assign
            </Button>
          </div>
          <ul className="divide-y divide-zinc-800">
            {published
              .filter((record) =>
                slot.assignedScenarioIds.includes(record.template.id),
              )
              .map((record) => {
                const version = activeVersion(record)!;
                const resolved =
                  attempt.ticketOverlays[scenarioTicketId(version)]?.closure
                    ?.verifiedResolved === true;
                return (
                  <li
                    className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center"
                    key={record.template.id}
                  >
                    <div className="flex-1">
                      <strong>{record.template.title}</strong>
                      <div className="mt-1">
                        <Badge variant={resolved ? 'success' : 'amber'}>
                          {resolved ? 'Resolved' : 'Open'}
                        </Badge>
                      </div>
                    </div>
                    <Link
                      className="rounded-sm border border-sky-500/40 px-3 py-2 text-center text-xs font-bold uppercase text-sky-300"
                      href={`/admin/test-students/${slot.id}/scenarios/${record.template.id}`}
                    >
                      Open ticket
                    </Link>
                    <Button
                      onClick={() =>
                        setSlot(
                          setTestStudentScenarioAssignment(
                            slot.id,
                            record.template.id,
                            false,
                          ),
                        )
                      }
                    >
                      Unassign
                    </Button>
                  </li>
                );
              })}
          </ul>
        </div>
      </Card>

      <Card>
        <CardHeader
          meta={
            <Button onClick={() => setConfirmReset(true)}>Reset attempt</Button>
          }
          title="Attempt event timeline"
        />
        <div className="p-4">
          {events.length === 0 ? (
            <p className="text-sm text-zinc-500">No actions recorded.</p>
          ) : (
            <ol className="space-y-3">
              {events.map((event) => (
                <li
                  className="rounded-sm border border-zinc-800 p-3"
                  key={event.id}
                >
                  <div className="flex flex-wrap justify-between gap-2">
                    <code
                      className={
                        event.success ? 'text-emerald-400' : 'text-red-400'
                      }
                    >
                      {event.type}
                    </code>
                    <time className="text-xs text-zinc-500">
                      {event.createdAt}
                    </time>
                  </div>
                  <p className="mt-1 font-mono text-xs text-zinc-500">
                    {event.id}
                  </p>
                  <pre className="mt-2 overflow-auto text-xs text-zinc-400">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </li>
              ))}
            </ol>
          )}
        </div>
      </Card>

      <Modal
        description="This clears only this slot's admin attempt."
        onOpenChange={setConfirmReset}
        open={confirmReset}
        title="Reset test attempt?"
      >
        <p className="text-sm text-zinc-300">
          All actions, closures, and overlay changes for {slot.name} will be
          replaced by a fresh seeded attempt.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={() => setConfirmReset(false)}>Cancel</Button>
          <Button
            onClick={() => {
              const next = resetTestAttempt(slot.id, assignedVersions);
              setAttempt(next);
              setConfirmReset(false);
            }}
            variant="primary"
          >
            Reset now
          </Button>
        </div>
      </Modal>
    </div>
  );
}
