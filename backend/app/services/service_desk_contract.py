"""Shared semantic contract guard for the separately deployed Service Desk UI."""

from fastapi import Header, HTTPException

SERVICE_DESK_CONTRACT_VERSION = "2.0"
SERVICE_DESK_CONTRACT_HEADER = "X-Nexus-Service-Desk-Contract"


def require_service_desk_contract(
    contract_version: str | None = Header(
        default=None, alias=SERVICE_DESK_CONTRACT_HEADER
    ),
) -> None:
    """Reject writes from stale or incompatible Service Desk browser bundles."""
    if contract_version != SERVICE_DESK_CONTRACT_VERSION:
        raise HTTPException(
            status_code=409,
            detail=(
                "Service Desk was updated. Refresh the page before continuing."
            ),
        )
