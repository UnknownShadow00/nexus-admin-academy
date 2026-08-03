'use client';

import {
  SHIPPING_DEPARTMENTS,
  SHIPPING_EQUIPMENT,
  SHIPPING_SPEEDS,
  getDirectoryShippingAddress,
  type ShippingDepartment,
  type ShippingEquipmentName,
  type ShippingSpeed,
} from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  Input,
  Modal,
  PanelFrame,
  Select,
} from '@service-desk/ui';
import {
  IconArrowLeft,
  IconBox,
  IconCircleCheck,
  IconHelpCircle,
  IconPackageExport,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import { useShippingManagerSession } from './TicketSessionProvider';

type EquipmentQuantities = Partial<Record<ShippingEquipmentName, number>>;

const EMPTY_QUANTITIES: EquipmentQuantities = {};

export function ShippingManagerTool() {
  const {
    cancelShipment,
    computers,
    createShipment,
    directoryUsers,
    isHydrated,
    lastAddress,
    shipments,
  } = useShippingManagerSession();
  const [learnOpen, setLearnOpen] = useState(false);
  const [recipientId, setRecipientId] = useState('');
  const [recipientSearch, setRecipientSearch] = useState('');
  const [street, setStreet] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [postalCode, setPostalCode] = useState('');
  const [senderDepartment, setSenderDepartment] =
    useState<ShippingDepartment>('IT Department');
  const [quantities, setQuantities] =
    useState<EquipmentQuantities>(EMPTY_QUANTITIES);
  const [computerAssetTag, setComputerAssetTag] = useState('');
  const [speed, setSpeed] = useState<ShippingSpeed>('standard');
  const [includeReturnLabel, setIncludeReturnLabel] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [successEvent, setSuccessEvent] = useState<ActionEvent | null>(null);
  const [statusEvent, setStatusEvent] = useState<ActionEvent | null>(null);

  const selectedRecipient = directoryUsers.find(
    (user) => user.id === recipientId,
  );
  const computerQuantity = quantities.Computer ?? 0;

  useEffect(() => {
    const preselected = new URLSearchParams(window.location.search).get(
      'computer',
    );
    if (
      preselected &&
      computers.some((computer) => computer.assetTag === preselected)
    ) {
      setComputerAssetTag(preselected);
      setQuantities((current) => ({ ...current, Computer: 1 }));
    }
  }, [computers]);

  const equipment = useMemo(
    () =>
      SHIPPING_EQUIPMENT.flatMap((name) => {
        const quantity = quantities[name] ?? 0;
        return quantity > 0 ? [{ name, quantity }] : [];
      }),
    [quantities],
  );

  function selectRecipient(directoryUserId: string) {
    const user = directoryUsers.find(
      (candidate) => candidate.id === directoryUserId,
    );
    setRecipientId(directoryUserId);
    setRecipientSearch(user?.fullName ?? '');
    const address = getDirectoryShippingAddress(directoryUserId);
    if (address) {
      setStreet(address.street);
      setCity(address.city);
      setState(address.state);
      setPostalCode(address.postalCode);
    }
  }

  function updateEquipment(name: ShippingEquipmentName, quantity: number) {
    const normalized = Math.max(
      0,
      Math.min(name === 'Computer' ? 1 : 10, quantity),
    );
    setQuantities((current) => ({ ...current, [name]: normalized }));
    if (name === 'Computer' && normalized === 0) {
      setComputerAssetTag('');
    }
  }

  function submitShipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage('');
    if (
      !recipientId ||
      !recipientSearch.trim() ||
      !street.trim() ||
      !city.trim() ||
      !state.trim() ||
      !postalCode.trim()
    ) {
      setValidationMessage('Enter the full shipping address before shipping.');
      return;
    }
    if (equipment.length === 0) {
      setValidationMessage('Add at least one equipment item before shipping.');
      return;
    }
    if (computerQuantity > 0 && !computerAssetTag) {
      setValidationMessage('Select a provisioned PC from the shelf.');
      return;
    }

    const actionEvent = createShipment({
      recipientDirectoryUserId: recipientId,
      recipientName: recipientSearch,
      street,
      city,
      state,
      postalCode,
      senderDepartment,
      equipment,
      computerAssetTag: computerQuantity > 0 ? computerAssetTag : null,
      speed,
      includeReturnLabel,
    });
    if (!actionEvent.success) {
      setValidationMessage(
        actionEvent.rejectReason ?? 'The shipment could not be created.',
      );
      return;
    }
    setSuccessEvent(actionEvent);
    setStatusEvent(null);
  }

  function refillLastAddress() {
    if (lastAddress) {
      setRecipientId(lastAddress.recipientDirectoryUserId);
      setRecipientSearch(lastAddress.recipientName);
      setStreet(lastAddress.street);
      setCity(lastAddress.city);
      setState(lastAddress.state);
      setPostalCode(lastAddress.postalCode);
    }
    setQuantities({});
    setComputerAssetTag('');
    setIncludeReturnLabel(false);
    setValidationMessage('');
    setSuccessEvent(null);
  }

  return (
    <PanelFrame
      aria-labelledby="shipping-manager-title"
      className="mx-auto w-full max-w-4xl p-0"
      variant="contained"
    >
      <header className="border-b border-zinc-700 px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 self-start rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <Modal
            description="Shipments are instant simulation records; no carrier or payment service is contacted."
            onOpenChange={setLearnOpen}
            open={learnOpen}
            title="How does shipping work?"
            trigger={
              <Button variant="ghost">
                <IconHelpCircle aria-hidden="true" className="h-5 w-5" />
                How does shipping work?
              </Button>
            }
          >
            <p className="text-sm leading-relaxed text-zinc-300">
              Choose a directory recipient, build the package, and select a
              service level. A selected computer is consumed from PC Shelf when
              you ship it. Cancelling the shipment returns that PC to the shelf.
            </p>
          </Modal>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconPackageExport aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Equipment dispatch
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="shipping-manager-title"
            >
              Shipping Manager
            </h1>
          </div>
        </div>
      </header>

      <div className="p-4 sm:p-6">
        {successEvent ? (
          <Card className="flex min-h-72 flex-col items-center justify-center p-6 text-center">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300">
              <IconCircleCheck aria-hidden="true" className="h-9 w-9" />
            </span>
            <h2 className="mt-4 text-2xl font-bold text-zinc-100">
              Replacement shipped
            </h2>
            <p className="mt-2 max-w-lg text-sm text-zinc-400">
              The shipment was recorded instantly and any selected computer was
              removed from PC Shelf.
            </p>
            <Button
              className="mt-5"
              onClick={refillLastAddress}
              variant="primary"
            >
              <IconRefresh aria-hidden="true" className="h-4 w-4" />
              Refill Last Address
            </Button>
          </Card>
        ) : (
          <form className="grid gap-6" onSubmit={submitShipment}>
            <FormSection number="01" title="Recipient information">
              <Field label="Recipient name" required>
                <Input
                  autoComplete="off"
                  list="shipping-directory-roster"
                  onChange={(event) => {
                    const value = event.target.value;
                    setRecipientSearch(value);
                    const match = directoryUsers.find(
                      (user) => user.fullName === value,
                    );
                    if (match) {
                      selectRecipient(match.id);
                    } else {
                      setRecipientId('');
                    }
                  }}
                  placeholder="Search the directory roster"
                  value={recipientSearch}
                />
                <datalist id="shipping-directory-roster">
                  {directoryUsers.map((user) => (
                    <option key={user.id} value={user.fullName}>
                      {user.department}
                    </option>
                  ))}
                </datalist>
                {selectedRecipient ? (
                  <p className="mt-1 text-xs text-sky-300">
                    {selectedRecipient.jobTitle} ·{' '}
                    {selectedRecipient.department}
                  </p>
                ) : null}
              </Field>
              <Field label="Street address" required>
                <Input
                  onChange={(event) => setStreet(event.target.value)}
                  value={street}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="City" required>
                  <Input
                    onChange={(event) => setCity(event.target.value)}
                    value={city}
                  />
                </Field>
                <Field label="State" required>
                  <Input
                    onChange={(event) => setState(event.target.value)}
                    value={state}
                  />
                </Field>
                <Field label="Postal code" required>
                  <Input
                    onChange={(event) => setPostalCode(event.target.value)}
                    value={postalCode}
                  />
                </Field>
              </div>
            </FormSection>

            <FormSection number="02" title="Package details">
              <Field label="Sender (from) department">
                <Select
                  onChange={(event) =>
                    setSenderDepartment(
                      event.target.value as ShippingDepartment,
                    )
                  }
                  value={senderDepartment}
                >
                  {SHIPPING_DEPARTMENTS.map((department) => (
                    <option key={department}>{department}</option>
                  ))}
                </Select>
              </Field>

              <div>
                <p className="text-xs font-extrabold uppercase text-zinc-400">
                  Equipment to ship
                </p>
                <div className="mt-2 grid gap-2">
                  {SHIPPING_EQUIPMENT.map((name) => {
                    const quantity = quantities[name] ?? 0;
                    return (
                      <div
                        className="flex flex-col gap-3 rounded-sm border border-zinc-800 p-3 sm:flex-row sm:items-center sm:justify-between"
                        key={name}
                      >
                        <label className="flex items-center gap-3 text-sm font-semibold text-zinc-200">
                          <input
                            checked={quantity > 0}
                            className="h-4 w-4 accent-sky-500"
                            onChange={(event) =>
                              updateEquipment(
                                name,
                                event.target.checked ? 1 : 0,
                              )
                            }
                            type="checkbox"
                          />
                          {name}
                        </label>
                        <div className="flex items-center gap-2">
                          <Button
                            aria-label={`Decrease ${name} quantity`}
                            className="h-9 min-h-9 px-3"
                            disabled={quantity === 0}
                            onClick={() => updateEquipment(name, quantity - 1)}
                          >
                            −
                          </Button>
                          <span className="w-8 text-center font-mono text-sm text-zinc-200">
                            {quantity}
                          </span>
                          <Button
                            aria-label={`Increase ${name} quantity`}
                            className="h-9 min-h-9 px-3"
                            disabled={name === 'Computer' && quantity === 1}
                            onClick={() => updateEquipment(name, quantity + 1)}
                          >
                            +
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {computerQuantity > 0 ? (
                <Field label="Provisioned PC">
                  <Select
                    onChange={(event) =>
                      setComputerAssetTag(event.target.value)
                    }
                    value={computerAssetTag}
                  >
                    <option value="">Select a PC currently on the shelf</option>
                    {computers.map((computer) => (
                      <option key={computer.assetTag} value={computer.assetTag}>
                        {computer.assetTag} · {computer.operatingSystem}
                      </option>
                    ))}
                  </Select>
                  {computers.length === 0 ? (
                    <p className="mt-2 text-xs text-amber-300">
                      No provisioned computers are currently present on PC
                      Shelf.
                    </p>
                  ) : null}
                </Field>
              ) : null}
            </FormSection>

            <FormSection number="03" title="Shipping speed">
              <div className="grid gap-2 sm:grid-cols-2">
                {SHIPPING_SPEEDS.map((option) => (
                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-sm border p-3 text-sm ${
                      speed === option.id
                        ? 'border-sky-400 bg-sky-400/10 text-sky-200'
                        : 'border-zinc-800 text-zinc-300'
                    }`}
                    key={option.id}
                  >
                    <input
                      checked={speed === option.id}
                      className="accent-sky-500"
                      name="shipping-speed"
                      onChange={() => setSpeed(option.id)}
                      type="radio"
                    />
                    <span>
                      <span className="block font-bold">{option.label}</span>
                      <span className="text-xs text-zinc-400">
                        {option.detail}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              <label className="flex items-start gap-3 rounded-sm border border-zinc-800 p-3 text-sm text-zinc-300">
                <input
                  checked={includeReturnLabel}
                  className="mt-0.5 h-4 w-4 accent-sky-500"
                  onChange={(event) =>
                    setIncludeReturnLabel(event.target.checked)
                  }
                  type="checkbox"
                />
                <span>
                  <span className="block font-bold text-zinc-200">
                    Include return label
                  </span>
                  Add a prepaid label for the replaced or damaged device.
                </span>
              </label>
            </FormSection>

            {validationMessage ? (
              <p
                className="rounded-sm border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-200"
                role="alert"
              >
                {validationMessage}
              </p>
            ) : null}
            <Button disabled={!isHydrated} type="submit" variant="primary">
              <IconBox aria-hidden="true" className="h-5 w-5" />
              Ship
            </Button>
          </form>
        )}

        <section className="mt-8 border-t border-zinc-800 pt-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-extrabold uppercase tracking-widest text-sky-400">
                Shipment status
              </p>
              <h2 className="mt-1 text-lg font-bold text-zinc-100">
                Recent shipments
              </h2>
            </div>
            <Badge variant="sky">{shipments.length}</Badge>
          </div>
          {statusEvent && !statusEvent.success ? (
            <p className="mt-3 text-sm text-red-300" role="alert">
              {statusEvent.rejectReason}
            </p>
          ) : null}
          {shipments.length === 0 ? (
            <p className="mt-4 text-sm text-zinc-500">
              No shipments have been created in this attempt.
            </p>
          ) : (
            <div className="mt-4 grid gap-3">
              {shipments.map((shipment) => (
                <Card className="p-4" key={shipment.id}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-zinc-100">
                          {shipment.address.recipientName}
                        </p>
                        <Badge
                          variant={
                            shipment.status === 'shipped'
                              ? 'success'
                              : 'default'
                          }
                        >
                          {shipment.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm text-zinc-400">
                        {shipment.equipment
                          .map((item) => `${item.quantity}× ${item.name}`)
                          .join(', ')}
                      </p>
                      <p className="mt-1 font-mono text-xs text-zinc-500">
                        {shipment.computerAssetTag ?? 'No computer'} ·{' '}
                        {shipment.speed}
                      </p>
                    </div>
                    {shipment.status === 'shipped' ? (
                      <Button
                        onClick={() =>
                          setStatusEvent(cancelShipment(shipment.id))
                        }
                        variant="default"
                      >
                        <IconTrash aria-hidden="true" className="h-4 w-4" />
                        Cancel shipment
                      </Button>
                    ) : null}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </div>
    </PanelFrame>
  );
}

function FormSection({
  children,
  number,
  title,
}: {
  children: React.ReactNode;
  number: string;
  title: string;
}) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center gap-3 border-b border-zinc-800 pb-3">
        <span className="font-mono text-xs font-bold text-sky-400">
          {number}
        </span>
        <h2 className="text-base font-extrabold uppercase text-zinc-100">
          {title}
        </h2>
      </div>
      <div className="grid gap-4">{children}</div>
    </Card>
  );
}

function Field({
  children,
  label,
  required = false,
}: {
  children: React.ReactNode;
  label: string;
  required?: boolean;
}) {
  return (
    <label className="text-xs font-extrabold uppercase text-zinc-400">
      {label} {required ? <span className="text-red-400">*</span> : null}
      <div className="mt-2 normal-case">{children}</div>
    </label>
  );
}
