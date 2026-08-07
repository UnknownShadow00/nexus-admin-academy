'use client';

import {
  AssetStatus,
  DIRECTORY_GROUP_NAMES,
  DIRECTORY_USER_FIXTURES,
  Priority,
  TicketCategory,
  getScenario,
  publishVersion,
  saveDraftVersion,
  type ScenarioActionRule,
  type ScenarioHint,
  type ScenarioObjective,
  type ScenarioRecord,
  type ScenarioVersionDraftData,
} from '@service-desk/shared';
import {
  Button,
  Card,
  CardHeader,
  Input,
  Select,
  Textarea,
} from '@service-desk/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

function id(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 7)}`;
}

function defaultDraft(): ScenarioVersionDraftData {
  return {
    category: TicketCategory.Access,
    description: {
      businessImpact: '',
      issue: '',
      reportedByLine: 'Reported through the service portal.',
      troubleshooting: [],
    },
    device: {
      assetTag: '',
      deviceName: '',
      kind: 'laptop',
      operatingSystem: 'Windows 11',
      state: 'active',
    },
    difficulty: 'medium',
    explanation: '',
    forbiddenActions: [],
    hints: [],
    initialWorldState: {
      assetOverlaySeeds: {},
      chatMessageSeeds: [],
      directoryOverlaySeeds: {},
    },
    objectives: [],
    pointValue: 100,
    priority: Priority.Medium,
    requester: {
      contact: '',
      department: '',
      email: '',
      location: '',
      name: '',
    },
    requiredActions: [],
    sla: {
      dueAt: new Date(Date.now() + 4 * 60 * 60 * 1_000).toISOString(),
      target: '4 hours',
    },
    slug: '',
    title: '',
  };
}

function draftFromRecord(record: ScenarioRecord): ScenarioVersionDraftData {
  const editable =
    record.versions.find((version) => version.publishedAt === null) ??
    record.versions.find(
      (version) => version.id === record.template.activeVersionId,
    ) ??
    record.versions.at(-1);
  if (!editable) {
    return {
      ...defaultDraft(),
      category: record.template.category,
      priority: record.template.priority,
      slug: record.template.slug,
      title: record.template.title,
    };
  }
  const {
    id: _id,
    publishedAt: _publishedAt,
    scenarioId: _scenarioId,
    version: _version,
    ...content
  } = editable;
  return {
    ...content,
    category: record.template.category,
    priority: record.template.priority,
    slug: record.template.slug,
    title: record.template.title,
  };
}

function Field({ children, label }: { children: ReactNode; label: string }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-bold uppercase tracking-wide text-zinc-400">
        {label}
      </span>
      {children}
    </label>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <Card>
      <CardHeader title={title} />
      <div className="grid gap-4 p-4 md:grid-cols-2">{children}</div>
    </Card>
  );
}

function ActionRulesEditor({
  label,
  onChange,
  rules,
}: {
  label: string;
  onChange: (rules: ScenarioActionRule[]) => void;
  rules: ScenarioActionRule[];
}) {
  return (
    <Card>
      <CardHeader
        meta={
          <Button
            onClick={() =>
              onChange([
                ...rules,
                {
                  actionType: 'ticket.close',
                  description: '',
                  id: id('rule'),
                },
              ])
            }
            variant="soft"
          >
            Add row
          </Button>
        }
        title={label}
      />
      <div className="space-y-3 p-4">
        {rules.length === 0 ? (
          <p className="text-sm text-zinc-500">No rules configured.</p>
        ) : null}
        {rules.map((rule, index) => (
          <div
            className="grid gap-2 rounded-sm border border-zinc-800 p-3 md:grid-cols-[1fr_1.5fr_auto]"
            key={rule.id}
          >
            <Input
              aria-label={`${label} action type ${index + 1}`}
              onChange={(event) =>
                onChange(
                  rules.map((candidate) =>
                    candidate.id === rule.id
                      ? { ...candidate, actionType: event.target.value }
                      : candidate,
                  ),
                )
              }
              placeholder="directory.update_groups"
              value={rule.actionType}
            />
            <Input
              aria-label={`${label} description ${index + 1}`}
              onChange={(event) =>
                onChange(
                  rules.map((candidate) =>
                    candidate.id === rule.id
                      ? { ...candidate, description: event.target.value }
                      : candidate,
                  ),
                )
              }
              placeholder="What must (or must not) happen"
              value={rule.description}
            />
            <Button
              onClick={() =>
                onChange(rules.filter((candidate) => candidate.id !== rule.id))
              }
            >
              Remove
            </Button>
            <Input
              aria-label={`${label} payload match ${index + 1}`}
              className="md:col-span-2"
              defaultValue={
                rule.payloadMatch ? JSON.stringify(rule.payloadMatch) : ''
              }
              onBlur={(event) => {
                try {
                  const value = event.target.value.trim();
                  const payloadMatch = value
                    ? (JSON.parse(value) as Record<string, unknown>)
                    : undefined;
                  onChange(
                    rules.map((candidate) =>
                      candidate.id === rule.id
                        ? { ...candidate, payloadMatch }
                        : candidate,
                    ),
                  );
                } catch {
                  event.target.setCustomValidity('Enter valid JSON.');
                  event.target.reportValidity();
                }
              }}
              onInput={(event) => event.currentTarget.setCustomValidity('')}
              placeholder='Optional payload match, e.g. {"directoryUserId":"..."}'
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

function objectiveDefaults(
  predicateType: ScenarioObjective['predicateType'],
): Record<string, unknown> {
  const userId = DIRECTORY_USER_FIXTURES[0]?.id ?? '';
  switch (predicateType) {
    case 'action_event_occurred':
      return { actionType: 'ticket.close', payloadMatch: {} };
    case 'directory_group_membership':
      return {
        directoryUserId: userId,
        group: DIRECTORY_GROUP_NAMES[0],
        includes: true,
      };
    case 'directory_user_field':
      return { directoryUserId: userId, equals: false, field: 'locked' };
    case 'ticket_verified_resolved':
      return {};
  }
}

function ObjectiveParams({
  objective,
  update,
}: {
  objective: ScenarioObjective;
  update: (params: Record<string, unknown>) => void;
}) {
  const params = objective.predicateParams;
  if (objective.predicateType === 'ticket_verified_resolved') {
    return (
      <p className="text-xs text-zinc-500">
        Checks the synthetic scenario ticket closure.
      </p>
    );
  }
  if (objective.predicateType === 'action_event_occurred') {
    return (
      <div className="grid gap-2 md:grid-cols-2">
        <Input
          aria-label="Objective action type"
          onChange={(event) =>
            update({ ...params, actionType: event.target.value })
          }
          placeholder="directory.unlock_account"
          value={String(params.actionType ?? '')}
        />
        <Input
          aria-label="Objective payload match"
          defaultValue={JSON.stringify(params.payloadMatch ?? {})}
          onBlur={(event) => {
            try {
              update({
                ...params,
                payloadMatch: JSON.parse(event.target.value || '{}') as Record<
                  string,
                  unknown
                >,
              });
            } catch {
              event.target.setCustomValidity('Enter valid JSON.');
              event.target.reportValidity();
            }
          }}
          onInput={(event) => event.currentTarget.setCustomValidity('')}
          placeholder="Payload match JSON"
        />
      </div>
    );
  }
  return (
    <div className="grid gap-2 md:grid-cols-3">
      <Select
        aria-label="Objective directory user"
        onChange={(event) =>
          update({ ...params, directoryUserId: event.target.value })
        }
        value={String(params.directoryUserId ?? '')}
      >
        {DIRECTORY_USER_FIXTURES.map((user) => (
          <option key={user.id} value={user.id}>
            {user.fullName}
          </option>
        ))}
      </Select>
      {objective.predicateType === 'directory_group_membership' ? (
        <>
          <Select
            aria-label="Objective directory group"
            onChange={(event) =>
              update({ ...params, group: event.target.value })
            }
            value={String(params.group ?? '')}
          >
            {DIRECTORY_GROUP_NAMES.map((group) => (
              <option key={group}>{group}</option>
            ))}
          </Select>
          <Select
            aria-label="Membership expected"
            onChange={(event) =>
              update({ ...params, includes: event.target.value === 'true' })
            }
            value={String(params.includes !== false)}
          >
            <option value="true">Must be a member</option>
            <option value="false">Must not be a member</option>
          </Select>
        </>
      ) : (
        <>
          <Select
            aria-label="Objective directory field"
            onChange={(event) =>
              update({ ...params, field: event.target.value })
            }
            value={String(params.field ?? 'locked')}
          >
            <option value="locked">Locked</option>
            <option value="disabled">Disabled</option>
            <option value="mfaEnrolled">MFA enrolled</option>
          </Select>
          <Select
            aria-label="Directory field expected value"
            onChange={(event) =>
              update({ ...params, equals: event.target.value === 'true' })
            }
            value={String(params.equals === true)}
          >
            <option value="true">True</option>
            <option value="false">False</option>
          </Select>
        </>
      )}
    </div>
  );
}

export function ScenarioBuilder({
  existingScenarioId,
}: {
  existingScenarioId?: string;
}) {
  const router = useRouter();
  const [scenarioId] = useState(
    () => existingScenarioId ?? id('scenario-template'),
  );
  const [draft, setDraft] = useState<ScenarioVersionDraftData>(defaultDraft);
  const [record, setRecord] = useState<ScenarioRecord | null>(null);
  const [message, setMessage] = useState('');
  const [worldUserId, setWorldUserId] = useState(
    DIRECTORY_USER_FIXTURES[0]?.id ?? '',
  );
  const assets = useMemo(
    () => DIRECTORY_USER_FIXTURES.flatMap((user) => user.devices),
    [],
  );
  const [worldAssetTag, setWorldAssetTag] = useState(assets[0]?.assetTag ?? '');
  const [worldAssetStatus, setWorldAssetStatus] = useState<AssetStatus>(
    AssetStatus.Deployed,
  );
  const [chatContactId, setChatContactId] = useState(
    DIRECTORY_USER_FIXTURES[0]?.id ?? '',
  );
  const [chatSeedBody, setChatSeedBody] = useState('');

  useEffect(() => {
    if (!existingScenarioId) {
      return;
    }
    const found = getScenario(existingScenarioId);
    if (found) {
      setRecord(found);
      setDraft(draftFromRecord(found));
    }
  }, [existingScenarioId]);

  function persist() {
    const next = saveDraftVersion(scenarioId, draft);
    setRecord(next);
    setMessage(`Draft v${next.versions.at(-1)?.version ?? 1} saved locally.`);
    if (!existingScenarioId) {
      router.replace(`/admin/scenarios/${scenarioId}`);
    }
    return next;
  }

  function publish() {
    persist();
    try {
      const next = publishVersion(scenarioId);
      setRecord(next);
      setMessage(`Version ${next.versions.at(-1)?.version} published.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Publish failed.');
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase text-amber-400">
            {record ? `Template ${record.template.id}` : 'New template'}
          </p>
          <h1 className="text-2xl font-black">
            {draft.title || 'Untitled scenario'}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {record ? (
            <Link
              className="rounded-sm border border-zinc-700 px-4 py-2 text-sm font-bold uppercase text-zinc-300"
              href={`/admin/scenarios/${scenarioId}/preview`}
            >
              Preview
            </Link>
          ) : null}
          <Button onClick={persist}>Save Draft</Button>
          <Button onClick={publish} variant="primary">
            Publish Version
          </Button>
        </div>
      </div>
      {message ? (
        <p className="rounded-sm border border-sky-400/30 bg-sky-400/10 p-3 text-sm text-sky-200">
          {message}
        </p>
      ) : null}

      <Section title="Basics">
        <Field label="Title">
          <Input
            onChange={(event) =>
              setDraft({ ...draft, title: event.target.value })
            }
            value={draft.title}
          />
        </Field>
        <Field label="Slug">
          <Input
            onChange={(event) =>
              setDraft({ ...draft, slug: event.target.value })
            }
            value={draft.slug}
          />
        </Field>
        <Field label="Category">
          <Select
            onChange={(event) =>
              setDraft({
                ...draft,
                category: event.target.value as TicketCategory,
              })
            }
            value={draft.category}
          >
            {Object.values(TicketCategory).map((category) => (
              <option key={category}>{category}</option>
            ))}
          </Select>
        </Field>
        <Field label="Priority">
          <Select
            onChange={(event) =>
              setDraft({
                ...draft,
                priority: event.target.value as Priority,
              })
            }
            value={draft.priority}
          >
            {Object.values(Priority).map((priority) => (
              <option key={priority}>{priority}</option>
            ))}
          </Select>
        </Field>
        <Field label="Point value">
          <Input
            min={0}
            onChange={(event) =>
              setDraft({ ...draft, pointValue: Number(event.target.value) })
            }
            type="number"
            value={draft.pointValue}
          />
        </Field>
        <Field label="Difficulty">
          <Select
            onChange={(event) =>
              setDraft({
                ...draft,
                difficulty: event.target
                  .value as ScenarioVersionDraftData['difficulty'],
              })
            }
            value={draft.difficulty}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </Select>
        </Field>
        <div className="md:col-span-2">
          <Field label="Post-resolution explanation">
            <Textarea
              onChange={(event) =>
                setDraft({ ...draft, explanation: event.target.value })
              }
              value={draft.explanation}
            />
          </Field>
        </div>
      </Section>

      <Section title="Requester and device">
        {(
          [
            ['name', 'Requester name'],
            ['department', 'Department'],
            ['email', 'Email'],
            ['contact', 'Contact'],
            ['location', 'Location'],
          ] as const
        ).map(([key, label]) => (
          <Field key={key} label={label}>
            <Input
              onChange={(event) =>
                setDraft({
                  ...draft,
                  requester: { ...draft.requester, [key]: event.target.value },
                })
              }
              value={draft.requester[key]}
            />
          </Field>
        ))}
        <Field label="Asset tag">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                device: { ...draft.device, assetTag: event.target.value },
              })
            }
            value={draft.device.assetTag}
          />
        </Field>
        <Field label="Device name">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                device: { ...draft.device, deviceName: event.target.value },
              })
            }
            value={draft.device.deviceName}
          />
        </Field>
        <Field label="Device kind">
          <Select
            onChange={(event) =>
              setDraft({
                ...draft,
                device: {
                  ...draft.device,
                  kind: event.target
                    .value as ScenarioVersionDraftData['device']['kind'],
                },
              })
            }
            value={draft.device.kind}
          >
            <option value="desktop">Desktop</option>
            <option value="laptop">Laptop</option>
            <option value="mobile">Mobile</option>
            <option value="peripheral">Peripheral</option>
          </Select>
        </Field>
        <Field label="Operating system">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                device: {
                  ...draft.device,
                  operatingSystem: event.target.value,
                },
              })
            }
            value={draft.device.operatingSystem}
          />
        </Field>
        <Field label="Device state">
          <Select
            onChange={(event) =>
              setDraft({
                ...draft,
                device: {
                  ...draft.device,
                  state: event.target
                    .value as ScenarioVersionDraftData['device']['state'],
                },
              })
            }
            value={draft.device.state}
          >
            <option value="active">Active</option>
            <option value="attention">Attention</option>
            <option value="offline">Offline</option>
          </Select>
        </Field>
      </Section>

      <Section title="Description and SLA">
        <div className="md:col-span-2">
          <Field label="Issue">
            <Textarea
              onChange={(event) =>
                setDraft({
                  ...draft,
                  description: {
                    ...draft.description,
                    issue: event.target.value,
                  },
                })
              }
              value={draft.description.issue}
            />
          </Field>
        </div>
        <Field label="Reported by line">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                description: {
                  ...draft.description,
                  reportedByLine: event.target.value,
                },
              })
            }
            value={draft.description.reportedByLine}
          />
        </Field>
        <Field label="Business impact">
          <Textarea
            onChange={(event) =>
              setDraft({
                ...draft,
                description: {
                  ...draft.description,
                  businessImpact: event.target.value,
                },
              })
            }
            value={draft.description.businessImpact}
          />
        </Field>
        <div className="md:col-span-2">
          <Field label="Troubleshooting (one step per line)">
            <Textarea
              onChange={(event) =>
                setDraft({
                  ...draft,
                  description: {
                    ...draft.description,
                    troubleshooting: event.target.value.split('\n'),
                  },
                })
              }
              value={draft.description.troubleshooting.join('\n')}
            />
          </Field>
        </div>
        <Field label="SLA due at">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                sla: { ...draft.sla, dueAt: event.target.value },
              })
            }
            type="datetime-local"
            value={draft.sla.dueAt.slice(0, 16)}
          />
        </Field>
        <Field label="SLA target label">
          <Input
            onChange={(event) =>
              setDraft({
                ...draft,
                sla: { ...draft.sla, target: event.target.value },
              })
            }
            value={draft.sla.target}
          />
        </Field>
      </Section>

      <Card>
        <CardHeader title="Initial world state overlays" />
        <div className="space-y-5 p-4">
          <div className="flex flex-col gap-2 md:flex-row">
            <Select
              aria-label="Directory user seed"
              onChange={(event) => setWorldUserId(event.target.value)}
              value={worldUserId}
            >
              {DIRECTORY_USER_FIXTURES.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.fullName}
                </option>
              ))}
            </Select>
            <Button
              onClick={() =>
                setDraft({
                  ...draft,
                  initialWorldState: {
                    ...draft.initialWorldState,
                    directoryOverlaySeeds: {
                      ...draft.initialWorldState.directoryOverlaySeeds,
                      [worldUserId]: draft.initialWorldState
                        .directoryOverlaySeeds[worldUserId] ?? {
                        groupChanges: { added: [], removed: [] },
                      },
                    },
                  },
                })
              }
              variant="soft"
            >
              Add directory seed
            </Button>
          </div>
          {Object.entries(draft.initialWorldState.directoryOverlaySeeds).map(
            ([userId, seed]) => (
              <div
                className="rounded-sm border border-zinc-800 p-3"
                key={userId}
              >
                <div className="flex items-center justify-between">
                  <strong>
                    {DIRECTORY_USER_FIXTURES.find((user) => user.id === userId)
                      ?.fullName ?? userId}
                  </strong>
                  <Button
                    onClick={() => {
                      const next = {
                        ...draft.initialWorldState.directoryOverlaySeeds,
                      };
                      delete next[userId];
                      setDraft({
                        ...draft,
                        initialWorldState: {
                          ...draft.initialWorldState,
                          directoryOverlaySeeds: next,
                        },
                      });
                    }}
                  >
                    Remove
                  </Button>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-4">
                  {(['locked', 'disabled', 'mfaEnrolled'] as const).map(
                    (field) => (
                      <label
                        className="flex items-center gap-2 text-sm"
                        key={field}
                      >
                        <input
                          checked={seed[field] === true}
                          onChange={(event) =>
                            setDraft({
                              ...draft,
                              initialWorldState: {
                                ...draft.initialWorldState,
                                directoryOverlaySeeds: {
                                  ...draft.initialWorldState
                                    .directoryOverlaySeeds,
                                  [userId]: {
                                    ...seed,
                                    [field]: event.target.checked,
                                  },
                                },
                              },
                            })
                          }
                          type="checkbox"
                        />
                        {field}
                      </label>
                    ),
                  )}
                  <Field label="Group add">
                    <Select
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          initialWorldState: {
                            ...draft.initialWorldState,
                            directoryOverlaySeeds: {
                              ...draft.initialWorldState.directoryOverlaySeeds,
                              [userId]: {
                                ...seed,
                                groupChanges: {
                                  added: event.target.value
                                    ? [event.target.value]
                                    : [],
                                  removed: seed.groupChanges?.removed ?? [],
                                },
                              },
                            },
                          },
                        })
                      }
                      value={seed.groupChanges?.added[0] ?? ''}
                    >
                      <option value="">None</option>
                      {DIRECTORY_GROUP_NAMES.map((group) => (
                        <option key={group}>{group}</option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Group remove">
                    <Select
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          initialWorldState: {
                            ...draft.initialWorldState,
                            directoryOverlaySeeds: {
                              ...draft.initialWorldState.directoryOverlaySeeds,
                              [userId]: {
                                ...seed,
                                groupChanges: {
                                  added: seed.groupChanges?.added ?? [],
                                  removed: event.target.value
                                    ? [event.target.value]
                                    : [],
                                },
                              },
                            },
                          },
                        })
                      }
                      value={seed.groupChanges?.removed[0] ?? ''}
                    >
                      <option value="">None</option>
                      {DIRECTORY_GROUP_NAMES.map((group) => (
                        <option key={group}>{group}</option>
                      ))}
                    </Select>
                  </Field>
                </div>
              </div>
            ),
          )}
          <div className="flex flex-col gap-2 border-t border-zinc-800 pt-4 md:flex-row">
            <Select
              aria-label="Asset seed"
              onChange={(event) => setWorldAssetTag(event.target.value)}
              value={worldAssetTag}
            >
              {assets.map((asset) => (
                <option key={asset.assetTag} value={asset.assetTag}>
                  {asset.assetTag} — {asset.deviceType}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Asset status override"
              onChange={(event) =>
                setWorldAssetStatus(event.target.value as AssetStatus)
              }
              value={worldAssetStatus}
            >
              {Object.values(AssetStatus).map((status) => (
                <option key={status}>{status}</option>
              ))}
            </Select>
            <Button
              onClick={() =>
                setDraft({
                  ...draft,
                  initialWorldState: {
                    ...draft.initialWorldState,
                    assetOverlaySeeds: {
                      ...draft.initialWorldState.assetOverlaySeeds,
                      [worldAssetTag]: { status: worldAssetStatus },
                    },
                  },
                })
              }
              variant="soft"
            >
              Set asset override
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(draft.initialWorldState.assetOverlaySeeds).map(
              ([assetTag, seed]) => (
                <Button
                  key={assetTag}
                  onClick={() => {
                    const next = {
                      ...draft.initialWorldState.assetOverlaySeeds,
                    };
                    delete next[assetTag];
                    setDraft({
                      ...draft,
                      initialWorldState: {
                        ...draft.initialWorldState,
                        assetOverlaySeeds: next,
                      },
                    });
                  }}
                >
                  {assetTag}: {seed.status ?? 'default'} ×
                </Button>
              ),
            )}
          </div>
          <div className="grid gap-2 border-t border-zinc-800 pt-4 md:grid-cols-[1fr_2fr_auto]">
            <Select
              aria-label="Chat seed contact"
              onChange={(event) => setChatContactId(event.target.value)}
              value={chatContactId}
            >
              {DIRECTORY_USER_FIXTURES.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.fullName}
                </option>
              ))}
            </Select>
            <Input
              aria-label="Seed chat message"
              onChange={(event) => setChatSeedBody(event.target.value)}
              placeholder="Initial message from this contact"
              value={chatSeedBody}
            />
            <Button
              disabled={!chatSeedBody.trim()}
              onClick={() => {
                setDraft({
                  ...draft,
                  initialWorldState: {
                    ...draft.initialWorldState,
                    chatMessageSeeds: [
                      ...draft.initialWorldState.chatMessageSeeds,
                      {
                        body: chatSeedBody.trim(),
                        contactId: chatContactId,
                      },
                    ],
                  },
                });
                setChatSeedBody('');
              }}
              variant="soft"
            >
              Add chat seed
            </Button>
          </div>
          <ul className="space-y-2">
            {draft.initialWorldState.chatMessageSeeds.map((seed, index) => (
              <li
                className="flex items-center justify-between gap-3 rounded-sm border border-zinc-800 p-3 text-sm"
                key={`${seed.contactId}-${index}`}
              >
                <span>
                  {DIRECTORY_USER_FIXTURES.find(
                    (user) => user.id === seed.contactId,
                  )?.fullName ?? seed.contactId}
                  : {seed.body}
                </span>
                <Button
                  onClick={() =>
                    setDraft({
                      ...draft,
                      initialWorldState: {
                        ...draft.initialWorldState,
                        chatMessageSeeds:
                          draft.initialWorldState.chatMessageSeeds.filter(
                            (_, candidateIndex) => candidateIndex !== index,
                          ),
                      },
                    })
                  }
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </Card>

      <ActionRulesEditor
        label="Required actions"
        onChange={(requiredActions) => setDraft({ ...draft, requiredActions })}
        rules={draft.requiredActions}
      />
      <ActionRulesEditor
        label="Forbidden actions"
        onChange={(forbiddenActions) =>
          setDraft({ ...draft, forbiddenActions })
        }
        rules={draft.forbiddenActions}
      />

      <Card>
        <CardHeader
          meta={
            <Button
              onClick={() =>
                setDraft({
                  ...draft,
                  objectives: [
                    ...draft.objectives,
                    {
                      description: '',
                      id: id('objective'),
                      order: draft.objectives.length + 1,
                      pointValue: 25,
                      predicateParams: objectiveDefaults(
                        'action_event_occurred',
                      ),
                      predicateType: 'action_event_occurred',
                      required: true,
                    },
                  ],
                })
              }
              variant="soft"
            >
              Add objective
            </Button>
          }
          title="Objectives"
        />
        <div className="space-y-3 p-4">
          {draft.objectives.map((objective, index) => {
            const replace = (next: ScenarioObjective) =>
              setDraft({
                ...draft,
                objectives: draft.objectives.map((candidate) =>
                  candidate.id === objective.id ? next : candidate,
                ),
              });
            return (
              <div
                className="space-y-3 rounded-sm border border-zinc-800 p-3"
                key={objective.id}
              >
                <div className="grid gap-2 md:grid-cols-[2fr_1.5fr_7rem_auto]">
                  <Input
                    aria-label={`Objective ${index + 1} description`}
                    onChange={(event) =>
                      replace({ ...objective, description: event.target.value })
                    }
                    placeholder="Objective description"
                    value={objective.description}
                  />
                  <Select
                    aria-label={`Objective ${index + 1} predicate`}
                    onChange={(event) => {
                      const predicateType = event.target
                        .value as ScenarioObjective['predicateType'];
                      replace({
                        ...objective,
                        predicateParams: objectiveDefaults(predicateType),
                        predicateType,
                      });
                    }}
                    value={objective.predicateType}
                  >
                    <option value="action_event_occurred">Action event</option>
                    <option value="directory_group_membership">
                      Directory group
                    </option>
                    <option value="directory_user_field">
                      Directory field
                    </option>
                    <option value="ticket_verified_resolved">
                      Verified ticket close
                    </option>
                  </Select>
                  <Input
                    aria-label={`Objective ${index + 1} points`}
                    min={0}
                    onChange={(event) =>
                      replace({
                        ...objective,
                        pointValue: Number(event.target.value),
                      })
                    }
                    type="number"
                    value={objective.pointValue}
                  />
                  <Button
                    onClick={() =>
                      setDraft({
                        ...draft,
                        objectives: draft.objectives
                          .filter((candidate) => candidate.id !== objective.id)
                          .map((candidate, order) => ({
                            ...candidate,
                            order: order + 1,
                          })),
                      })
                    }
                  >
                    Remove
                  </Button>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={objective.required}
                    onChange={(event) =>
                      replace({ ...objective, required: event.target.checked })
                    }
                    type="checkbox"
                  />
                  Required objective
                </label>
                <ObjectiveParams
                  objective={objective}
                  update={(predicateParams) =>
                    replace({ ...objective, predicateParams })
                  }
                />
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardHeader
          meta={
            <Button
              onClick={() => {
                const hint: ScenarioHint = {
                  id: id('hint'),
                  order: draft.hints.length + 1,
                  pointPenalty: 0,
                  text: '',
                };
                setDraft({ ...draft, hints: [...draft.hints, hint] });
              }}
              variant="soft"
            >
              Add hint
            </Button>
          }
          title="Hints"
        />
        <div className="space-y-3 p-4">
          {draft.hints.map((hint, index) => (
            <div
              className="grid gap-2 md:grid-cols-[1fr_8rem_auto]"
              key={hint.id}
            >
              <Textarea
                aria-label={`Hint ${index + 1}`}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    hints: draft.hints.map((candidate) =>
                      candidate.id === hint.id
                        ? { ...candidate, text: event.target.value }
                        : candidate,
                    ),
                  })
                }
                value={hint.text}
              />
              <Input
                aria-label={`Hint ${index + 1} point penalty`}
                min={0}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    hints: draft.hints.map((candidate) =>
                      candidate.id === hint.id
                        ? {
                            ...candidate,
                            pointPenalty: Number(event.target.value),
                          }
                        : candidate,
                    ),
                  })
                }
                type="number"
                value={hint.pointPenalty}
              />
              <Button
                onClick={() =>
                  setDraft({
                    ...draft,
                    hints: draft.hints
                      .filter((candidate) => candidate.id !== hint.id)
                      .map((candidate, order) => ({
                        ...candidate,
                        order: order + 1,
                      })),
                  })
                }
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {record && record.versions.length > 1 ? (
        <Card>
          <CardHeader title="Version history" />
          <ol className="divide-y divide-zinc-800 p-4">
            {record.versions.map((version) => (
              <li className="flex justify-between gap-4 py-2" key={version.id}>
                <span>Version {version.version}</span>
                <span className="text-sm text-zinc-500">
                  {version.publishedAt
                    ? new Date(version.publishedAt).toLocaleString()
                    : 'Current draft'}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
    </div>
  );
}
