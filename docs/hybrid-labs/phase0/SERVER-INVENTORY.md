# Hybrid Labs Phase 0 — Server Inventory

Date: 2026-09-10 UTC

Scope: read-only discovery; no Proxmox, VM, LXC, storage, network, firewall, or application state was changed.

## Evidence boundary

The shell is running inside the Nexus application VM, `nexus-services`, not on the Proxmox node. The actual Proxmox web endpoint was identified at `https://192.168.0.50:8006`; its certificate identifies the node as `pve.home.lan` and includes `192.168.100.2`. The current account has neither an authorized SSH path nor a configured Proxmox API token. Therefore hypervisor-only facts are explicitly `UNKNOWN` rather than inferred from guest metrics.

## Exact commands and material results

| Command | Result |
|---|---|
| `hostnamectl` | `nexus-services`; Ubuntu 26.04 LTS; chassis `vm`; virtualization `kvm`; QEMU i440FX guest |
| `command -v pveversion pvesh qm pct` | No Proxmox CLI commands installed in the Nexus guest |
| `curl -ksS https://192.168.0.50:8006/` | HTTP 200 with title `pve - Proxmox Virtual Environment` |
| `openssl s_client -connect 192.168.0.50:8006 ...` | Certificate CN `pve.home.lan`; SAN contains `192.168.100.2`, `pve`, and `pve.home.lan`; no secret material |
| `curl -ksS https://192.168.0.50:8006/api2/json/version` | No version data without authentication |
| `ssh -o BatchMode=yes ... root@192.168.0.50 'hostname; pveversion --verbose'` | `Permission denied (publickey,password)`; no interactive password attempt was made |
| Equivalent batch SSH as `nexus` and `admin` | Permission denied; no interactive password attempt was made |
| Inspection of live service environment and `backend/.env` for named integration keys | No `PROXMOX_*`, `GUACAMOLE_*`, or `LAB_VM_*` settings configured; secret values were never printed |
| `lscpu` in Nexus guest | 4 vCPUs; `QEMU Virtual CPU version 2.5+`; KVM; no `vmx`/`svm` flag exposed |
| `free -h` in Nexus guest | 7.3 GiB total, 2.9 GiB used, 447 MiB free, 4.4 GiB available |
| `swapon --show --bytes` | 4.0 GiB swap file; about 3.2 GiB used at inspection time |
| `uptime` | 45 days, 32 minutes; load averages 0.49, 0.39, 0.23 |
| `df -hT -x tmpfs -x devtmpfs` | Guest root: 57 GiB total, 53 GiB used, 2.0 GiB available, 97% by `df` |
| `lsblk` | One 60 GiB virtual disk; 58 GiB LVM PV/root LV plus 2 GiB boot partition |
| `ip -brief address` | Nexus VM `ens18` is `192.168.0.101/24`; Docker bridges are `172.17.0.0/16` through `172.20.0.0/16` |
| `ip route get 192.168.0.50` | Directly connected via `ens18`; no router hop |
| `docker ps` | Running: `nexus-frontend` and `nexus-service-desk`; no Guacamole, PostgreSQL, or Proxmox integration container |
| `systemctl status nexus-admin-academy.service` | Backend active since 2026-09-09 06:41 UTC; bound to `172.17.0.1:8000` |

Commands that would mutate guest or hypervisor state were not run. The HTTPS requests above were read-only identification attempts.

## Actual Proxmox host

| Item | Result | Phase 1 implication |
|---|---|---|
| Node identity | Endpoint `192.168.0.50:8006`; certificate says `pve.home.lan` / internal SAN `192.168.100.2` | Confirm the intended management address and routing model with an operator |
| Proxmox version | **UNKNOWN** | Read with `pveversion --verbose` or `/api2/json/version` using a read-only audit identity |
| Physical CPU model | **UNKNOWN** | Read from `lscpu` on PVE or node status API |
| Physical cores / threads | **UNKNOWN** | Required before capacity approval |
| Hardware virtualization | **UNKNOWN** | Guest is KVM, proving virtualization exists, but not CPU flags or BIOS state on the node |
| Nested virtualization | **UNKNOWN** | The Nexus guest does not expose `vmx`/`svm`; nested virtualization is not needed for INC2504 |
| Total / used / available RAM | **UNKNOWN** | Required before allocating 6–8 GiB to Windows |
| Host swap | **UNKNOWN** | Required; sustained host swap would be a no-go signal |
| Host uptime / load | **UNKNOWN** | Required for a representative utilization baseline |

## Storage inventory

All Proxmox storage facts are **UNKNOWN** because neither PVE shell nor authenticated API access was available:

- configured backends (`local`, `local-lvm`, ZFS, Ceph, NFS, and so on);
- total, used, and free physical capacity;
- thin-provisioning data and metadata usage;
- snapshot support;
- linked-clone support for the eventual template's actual volumes;
- current VM/template provisioned disk totals and actual physical consumption.

The Nexus guest's 60 GiB virtual disk is not a measure of Proxmox free storage. Its root filesystem is nevertheless operationally concerning at 97% full.

### Provisioned versus actual usage

- **Provisioned disk** is the guest-visible maximum, such as an 80 GiB Windows virtual disk. It is a promise/limit, not necessarily 80 GiB already consumed.
- **Actual physical usage** is the allocated data on the backing store, including template/base images, changed blocks, snapshots, metadata, and storage overhead.
- A linked clone can have an 80 GiB provisioned size while initially consuming only changed blocks, but growth and snapshot retention still require physical headroom.
- Phase 1 must use backend-specific physical metrics (for example LVM-thin data/metadata percentages or ZFS pool allocation), not just the sum of virtual disk sizes.

## VM and LXC inventory

VMID, name, type, state, CPU allocation, RAM allocation, disk allocation, bridge, and interface inventory are all **UNKNOWN**. No `qm list`, `pct list`, or authenticated cluster-resource result could be obtained. ARP entries with QEMU OUIs were not treated as a VM inventory because that would be unreliable.

Known workload facts from inside the Nexus guest:

- Nexus backend: systemd-hosted FastAPI/Uvicorn on the Docker gateway address.
- Nexus frontend: `nginx:alpine` container, published on TCP 80.
- Service Desk: `nexus-service-desk` container, loopback-published on TCP 13000.
- Database: live configuration uses a local SQLite URL; production data was not queried.
- Docker: active on this Nexus VM with the `nexus-production` network at `172.19.0.0/16`.
- Guacamole: no live container/service and no environment configuration found.
- Other Proxmox guests/LXCs: **UNKNOWN**.

## Windows template and licensing

### Template

**UNKNOWN — NOT VERIFIED ON PROXMOX.** The repository contains curriculum prose naming `WS2022-DC` and `Win11-Enterprise`, but no non-test `proxmox_template_vmid` is configured in source, and those names do not prove a current VM/template exists. Windows version, template flag, guest agent, RDP readiness, TPM, UEFI/OVMF, RAM, CPU, disk, and snapshot state could not be inspected.

### Licensing

**UNVERIFIED — BLOCKER BEFORE STUDENT USE.** No repository or live service configuration provides reliable Windows license entitlement evidence. No product key was sought or displayed, and activation was not attempted. A future time-limited POC may use a lawful Microsoft evaluation only after its terms and expiry handling are documented.

## Capacity classification

These classifications deliberately do not convert guest metrics into host capacity.

| Scenario | RAM | CPU | Disk / I/O | Classification |
|---|---|---|---|---|
| A. Current Nexus workloads only | Guest has 4.4 GiB available but 3.2 GiB swap in use | Guest load is currently low | Guest root has only 2.0 GiB free | **POSSIBLE WITH LIMITS** — it is running, but guest disk pressure needs attention outside this phase |
| B. Nexus + one Windows lab | Host headroom unknown; needs 6–8 GiB plus safety reserve | Host model/cores unknown | Needs about 80 GiB provisioned and measured physical reserve | **NOT RECOMMENDED** until host inventory passes |
| C. Nexus + two Windows labs | Needs 12–16 GiB lab RAM plus workload and reserve | Concurrency and contention unknown | Clone growth and simultaneous I/O unknown | **NOT RECOMMENDED** |
| D. Nexus + Windows + small Linux endpoint | Needs 6.5–9 GiB lab RAM plus reserve | Likely modest endpoint CPU, but host unknown | About 85–90 GiB provisioned; actual use unknown | **NOT RECOMMENDED** until measured; this is the intended POC topology |
| E. Future small network lab | Topology-dependent and likely additive | Packet capture/network emulation can burst | Image and write-amplification risk unknown | **NOT RECOMMENDED** on current evidence |

Approval thresholds proposed for one POC attempt: keep at least 8 GiB host-available RAM after reservations, avoid sustained host swapping, retain at least 100 GiB genuinely free physical storage (or a documented thin-pool growth/alert plan), and measure clone/boot I/O during an operator-controlled staging test. These are operational guardrails, not findings about current capacity.
