# INC2504 Hybrid-Lab POC Live-Test Notes

This branch prepares one controlled manual test. It does not deploy content,
change Proxmox, or enable the lab in production.

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

## Final manual test

With production still untouched, an operator may select stopped disposable
VM172 or another verified-free dynamic VMID, launch INC2504 once, confirm the
six final-state checks, exercise RDP through Guacamole, and end the assignment.
Do not run two INC2504 instances concurrently.
