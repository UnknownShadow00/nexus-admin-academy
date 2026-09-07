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
  IconBox,
  IconCircleCheck,
  IconHelpCircle,
  IconPackageExport,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';
import { ToolBackLink } from './IntegratedToolContext';
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
      <header className="border-b border-border px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <ToolBackLink />
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
            <p className="text-sm leading-relaxed text-text">
              Choose a directory recipient, build the package, and select a
              service level. A selected computer is consumed from PC Shelf when
              you ship it. Cancelling the shipment returns that PC to the shelf.
            </p>
          </Modal>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-accent/30 bg-accent/10 text-accent">
            <IconPackageExport aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="text-xs font-extrabold uppercase tracking-widest text-accent">
              Equipment dispatch
            </p>
            <h1
              className="font-display text-2xl font-bold text-text"
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
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-success/15 text-success">
              <IconCircleCheck aria-hidden="true" className="h-9 w-9" />
            </span>
            <h2 className="mt-4 text-2xl font-bold text-text">
              Replacement shipped
            </h2>
            <p className="mt-2 max-w-lg text-sm text-text-muted">
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
                  <p className="mt-1 text-xs text-accent">
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
                <p className="text-xs font-extrabold uppercase text-text-muted">
                  Equipment to ship
                </p>
                <div className="mt-2 grid gap-2">
                  {SHIPPING_EQUIPMENT.map((name) => {
                    const quantity = quantities[name] ?? 0;
                    return (
                      <div
                        className="flex flex-col gap-3 rounded-sm border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
                        key={name}
                      >
                        <label className="flex items-center gap-3 text-sm font-semibold text-text">
                          <input
                            checked={quantity > 0}
                            className="h-4 w-4 accent-accent"
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
                          <span className="w-8 text-center font-mono text-sm text-text">
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
                    <p className="mt-2 text-xs text-warning">
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
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border text-text'
                    }`}
                    key={option.id}
                  >
                    <input
                      checked={speed === option.id}
                      className="accent-accent"
                      name="shipping-speed"
                      onChange={() => setSpeed(option.id)}
                      type="radio"
                    />
                    <span>
                      <span className="block font-bold">{option.label}</span>
                      <span className="text-xs text-text-muted">
                        {option.detail}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              <label className="flex items-start gap-3 rounded-sm border border-border p-3 text-sm text-text">
                <input
                  checked={includeReturnLabel}
                  className="mt-0.5 h-4 w-4 accent-accent"
                  onChange={(event) =>
                    setIncludeReturnLabel(event.target.checked)
                  }
                  type="checkbox"
                />
                <span>
                  <span className="block font-bold text-text">
                    Include return label
                  </span>
                  Add a prepaid label for the replaced or damaged device.
                </span>
              </label>
            </FormSection>

            {validationMessage ? (
              <p
                className="rounded-sm border border-danger/40 bg-danger/10 px-4 py-3 text-sm font-semibold text-danger"
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

        <section className="mt-8 border-t border-border pt-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-extrabold uppercase tracking-widest text-accent">
                Shipment status
              </p>
              <h2 className="mt-1 text-lg font-bold text-text">
                Recent shipments
              </h2>
            </div>
            <Badge variant="sky">{shipments.length}</Badge>
          </div>
          {statusEvent && !statusEvent.success ? (
            <p className="mt-3 text-sm text-danger" role="alert">
              {statusEvent.rejectReason}
            </p>
          ) : null}
          {shipments.length === 0 ? (
            <p className="mt-4 text-sm text-text-muted">
              No shipments have been created in this attempt.
            </p>
          ) : (
            <div className="mt-4 grid gap-3">
              {shipments.map((shipment) => (
                <Card className="p-4" key={shipment.id}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-text">
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
                      <p className="mt-1 text-sm text-text-muted">
                        {shipment.equipment
                          .map((item) => `${item.quantity}× ${item.name}`)
                          .join(', ')}
                      </p>
                      <p className="mt-1 font-mono text-xs text-text-muted">
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
      <div className="mb-4 flex items-center gap-3 border-b border-border pb-3">
        <span className="font-mono text-xs font-bold text-accent">
          {number}
        </span>
        <h2 className="text-base font-extrabold uppercase text-text">
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
    <label className="text-xs font-extrabold uppercase text-text-muted">
      {label} {required ? <span className="text-danger">*</span> : null}
      <div className="mt-2 normal-case">{children}</div>
    </label>
  );
}
