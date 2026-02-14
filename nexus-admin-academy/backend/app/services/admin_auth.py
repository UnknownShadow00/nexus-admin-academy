import os

from fastapi import Header, HTTPException


async def verify_admin(x_admin_key: str | None = Header(default=None, alias="X-ADMIN-KEY")) -> bool:
    expected = os.getenv("ADMIN_SECRET_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_SECRET_KEY is not configured")
    if x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return True
