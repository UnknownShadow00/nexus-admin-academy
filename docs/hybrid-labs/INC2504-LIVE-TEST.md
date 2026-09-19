# INC2504 Hybrid-Lab POC Live-Test Notes

The controlled live POC passed end to end on 2026-09-19. This branch does not
deploy content or enable the lab in production.

## Live POC result

The controlled run successfully:

- cloned template VM173 into the `nexus-labs` resource pool with the enforced
  Nexus assignment-owned VM name;
- waited for the clone and start tasks, confirmed the VM was running, and
  reached Windows through the QEMU Guest Agent;
- ran the allowlisted `inc2504_printer_stale_ip` provisioner, tolerated the
  expected temporary guest-agent outage during the Windows reboot, and
  recovered after reboot;
- returned the exact final six-state verification:

```text
HOSTNAME=NX-2504
IP=10.10.10.10
PRINTER=Front Office Printer
PRINTER_PORT=IP_10.10.10.19
AUTOLOGIN=0
UNATTEND_EXISTS=False
```

- kept the generated temporary Windows password redacted and out of persisted
  Nexus state, files, logs, and API responses; and
- completed protected destruction after verifying the dynamic VMID, resource
  pool membership, and Nexus-owned name. Disposable VM172 was removed.

No secret, password, or token value is recorded in this document.

## POC boundaries

- The INC2504 provisioner is server allowlisted as
  `inc2504_printer_stale_ip`; `LabTemplate.break_script` is never executed.
- VM 173 is the template. Dynamic clones may use only unreserved VMIDs in
  170–179 and must be members of the `nexus-labs` pool with a Nexus-generated
  assignment name.
- `vmbr1` is a flat isolated layer-2 network. Every INC2504 clone uses
  `10.10.10.10`, so the API permits only one active INC2504 provisioner at a
  time. This is a POC guard, not multi-user network isolation.
- The generated Windows password exists only in process memory long enough to
  create the Guacamole RDP connection. It is not stored in Nexus records,
  files, logs, or API responses.
- A provisioning or final-verification failure triggers protected VM teardown
  and never advances the assignment to `running`.

## Required non-secret configuration

Use the values documented in `backend/.env.example`: node `pve`, pool
`nexus-labs`, dynamic range 170–179, reserved IDs 170/171/173, linked-clone
request with safe full-clone fallback, and SSL verification enabled. Supply
the host, token ID, and token secret through the deployment secret mechanism;
never commit or print them.

The live POC used `PROXMOX_VERIFY_SSL=false` only as a temporary test
exception. This produced `InsecureRequestWarning` messages and is not an
acceptable production configuration. Production must trust and verify the
Proxmox TLS certificate.

The least-privilege `NexusLabs` role required these privileges during the
successful live run:

- `Pool.Audit` (required to verify `nexus-labs` membership before protected
  destruction)
- `VM.Allocate`
- `VM.Audit`
- `VM.Clone`
- `VM.Config.Disk`
- `VM.GuestAgent.Audit`
- `VM.GuestAgent.Unrestricted`
- `VM.PowerMgmt`

## Remaining worker durability gap

VM lifecycle work still runs in FastAPI `BackgroundTasks`. Those tasks are not
durable across a process crash or restart:

- a task lost before it starts can leave an assignment in `provisioning` with
  `retry_count=0`;
- a task interrupted after it starts can leave an assignment in an
  intermediate state with `retry_count=1` and a discoverable VMID;
- cleanup work can likewise be interrupted.

Automatically replaying these records is not safe without a durable lease,
idempotent step checkpoints, and reconciliation of the persisted record with
actual Proxmox and Guacamole state. That is larger than this POC hardening
pass. Before production multi-user use, move lifecycle ownership to a durable
worker/reconciler. For the one controlled live test, avoid API restarts during
provisioning and use the admin assignment view plus protected cleanup path if
the process is interrupted.

## Production blockers

The implementation and controlled Proxmox/Windows lifecycle POC are complete,
but production rollout remains blocked by all of the following:

- Windows licensing and activation are unresolved.
- Shared `vmbr1` supports only one active INC2504 fixed-IP instance.
- The live Guacamole student-access path needs final production validation.
- A durable worker, reconciler, restart recovery, and orphan/cleanup retry path
  are still required; FastAPI `BackgroundTasks` is not a durable lifecycle
  mechanism.
- Proxmox TLS certificate verification must be addressed before production.
- Production secret provisioning is still required.
- Broader capacity and concurrency design is required before multi-user
  rollout.
