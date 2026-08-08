'use client';

import {
  listTestStudents,
  setTestStudentScenarioAssignment,
  type ScenarioRecord,
  type ScenarioVersion,
  type TestStudentSlot,
} from '@service-desk/shared';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  PriorityBadge,
  Select,
} from '@service-desk/ui';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { clearTestAttempt } from '../_lib/test-attempt';
import { getServerScenario } from '../../../lib/nexus-admin-scenario-client';

function displayVersion(record: ScenarioRecord): ScenarioVersion | undefined {
  return (
    record.versions.find(
      (version) => version.id === record.template.activeVersionId,
    ) ??
    record.versions.find((version) => version.publishedAt === null) ??
    record.versions.at(-1)
  );
}

export function ScenarioPreview({ scenarioId }: { scenarioId: string }) {
  const router = useRouter();
  const [record, setRecord] = useState<ScenarioRecord | null>(null);
  const [slots, setSlots] = useState<TestStudentSlot[]>([]);
  const [slotId, setSlotId] = useState('');

  useEffect(() => {
    const nextSlots = listTestStudents();
    void getServerScenario(scenarioId).then(setRecord);
    setSlots(nextSlots);
    setSlotId(nextSlots[0]?.id ?? '');
  }, [scenarioId]);

  if (!record) {
    return (
      <p className="text-zinc-400">Loading scenario from Nexus…</p>
    );
  }
  const version = displayVersion(record);
  if (!version) {
    return <p className="text-zinc-400">This scenario has no saved version.</p>;
  }
  const canLaunch = Boolean(record.template.activeVersionId && slotId);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge>{record.template.category}</Badge>
            <PriorityBadge pill priority={record.template.priority} />
            <Badge variant={version.publishedAt ? 'success' : 'amber'}>
              {version.publishedAt
                ? `Published v${version.version}`
                : `Draft v${version.version}`}
            </Badge>
          </div>
          <h1 className="mt-3 text-2xl font-black">{record.template.title}</h1>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Select
            aria-label="Test student slot"
            onChange={(event) => setSlotId(event.target.value)}
            value={slotId}
          >
            {slots.length === 0 ? (
              <option value="">Create a test student first</option>
            ) : null}
            {slots.map((slot) => (
              <option key={slot.id} value={slot.id}>
                {slot.name}
              </option>
            ))}
          </Select>
          <Button
            disabled={!canLaunch}
            onClick={() => {
              setTestStudentScenarioAssignment(slotId, scenarioId, true);
              clearTestAttempt(slotId);
              router.push(
                `/admin/test-students/${slotId}/scenarios/${scenarioId}`,
              );
            }}
            variant="primary"
          >
            Launch as test attempt
          </Button>
        </div>
      </div>
      {!record.template.activeVersionId ? (
        <p className="rounded-sm border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-200">
          Drafts can be previewed but cannot be assigned. Publish this version
          to launch it.
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Issue details" />
            <div className="space-y-5 p-4">
              <div>
                <p className="text-xs font-bold uppercase text-zinc-500">
                  {version.description.reportedByLine}
                </p>
                <p className="mt-2 text-zinc-200">
                  {version.description.issue}
                </p>
              </div>
              <div>
                <h2 className="text-xs font-bold uppercase text-zinc-500">
                  Troubleshooting already tried
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
            <CardHeader title="Admin-only objectives" />
            <ol className="space-y-3 p-4">
              {version.objectives.map((objective) => (
                <li
                  className="rounded-sm border border-zinc-800 p-3"
                  key={objective.id}
                >
                  <div className="flex justify-between gap-3">
                    <strong>
                      {objective.order}. {objective.description}
                    </strong>
                    <span>{objective.pointValue} pts</span>
                  </div>
                  <code className="mt-2 block overflow-auto text-xs text-zinc-500">
                    {objective.predicateType}{' '}
                    {JSON.stringify(objective.predicateParams)}
                  </code>
                </li>
              ))}
            </ol>
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
                <dt className="text-zinc-500">Email</dt>
                <dd>{version.requester.email}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Contact</dt>
                <dd>{version.requester.contact}</dd>
              </div>
            </dl>
          </Card>
          <Card>
            <CardHeader title="Device and SLA" />
            <dl className="space-y-2 p-4 text-sm">
              <div>
                <dt className="text-zinc-500">Device</dt>
                <dd>
                  {version.device.deviceName} ({version.device.assetTag})
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">OS</dt>
                <dd>{version.device.operatingSystem}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Target</dt>
                <dd>{version.sla.target}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Due</dt>
                <dd>{version.sla.dueAt}</dd>
              </div>
            </dl>
          </Card>
          <Card>
            <CardHeader title="Hints (collapsed)" />
            <div className="space-y-2 p-4">
              {version.hints.map((hint) => (
                <details
                  className="rounded-sm border border-zinc-800 p-3"
                  key={hint.id}
                >
                  <summary className="cursor-pointer font-bold">
                    Hint {hint.order} ({hint.pointPenalty} pt penalty)
                  </summary>
                  <p className="mt-2 text-sm text-zinc-300">{hint.text}</p>
                </details>
              ))}
            </div>
          </Card>
          <Card>
            <CardHeader title="Initial world state" />
            <div className="space-y-2 p-4 text-sm">
              <p>
                {
                  Object.keys(version.initialWorldState.directoryOverlaySeeds)
                    .length
                }{' '}
                directory overlays
              </p>
              <p>
                {
                  Object.keys(version.initialWorldState.assetOverlaySeeds)
                    .length
                }{' '}
                asset overlays
              </p>
              <p>
                {version.initialWorldState.chatMessageSeeds.length} chat
                messages
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
