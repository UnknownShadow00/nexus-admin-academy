"""Fail-closed dispatch for approved hybrid-lab VM provisioners."""

from collections.abc import Callable
from typing import Any


Provisioner = Callable[..., dict[str, str] | None]
APPROVED_PROVISIONERS: dict[str, Provisioner] = {}


def apply(handler: str, *, vmid: int, config: dict[str, Any]) -> dict[str, str] | None:
    provisioner = APPROVED_PROVISIONERS.get(handler)
    if provisioner is None:
        raise RuntimeError(f"Unsupported VM provisioning handler: {handler}")

    return provisioner(vmid=vmid, config=config)
