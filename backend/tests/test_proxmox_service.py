from unittest.mock import MagicMock

from app.services import proxmox_service


def _configure(monkeypatch, *, full_clone: bool):
    monkeypatch.setenv("PROXMOX_HOST", "pve.example")
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "automation@pve!labs")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "secret")
    monkeypatch.setenv("PROXMOX_NODE", "pve")
    monkeypatch.setenv("VMID_POOL_START", "200")
    monkeypatch.setenv("VMID_POOL_END", "299")
    monkeypatch.setenv("PROXMOX_FULL_CLONE", "true" if full_clone else "false")


def _mock_proxmox(storage_type="lvmthin"):
    proxmox = MagicMock()
    proxmox.cluster.resources.get.return_value = [{"vmid": 200}]
    node = proxmox.nodes("pve")
    node.qemu(900).config.get.return_value = {"scsi0": "local-lvm:vm-900-disk-0,size=20G"}
    node.storage.get.return_value = [{"storage": "local-lvm", "type": storage_type}]
    node.qemu(900).clone.post.return_value = None
    return proxmox


def test_linked_clone_passes_full_zero_on_supported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("lvmthin")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    assert proxmox_service.clone_template(900, "unique-lab-name") == 201
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="unique-lab-name", full=0
    )


def test_linked_clone_falls_back_to_full_on_unsupported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("dir")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "fallback-lab")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="fallback-lab", full=1
    )


def test_explicit_full_clone_skips_storage_probe(monkeypatch):
    _configure(monkeypatch, full_clone=True)
    proxmox = _mock_proxmox()
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "full-lab")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="full-lab", full=1
    )
    proxmox.nodes("pve").qemu(900).config.get.assert_not_called()

