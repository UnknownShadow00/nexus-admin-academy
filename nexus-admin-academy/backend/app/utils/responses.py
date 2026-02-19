def ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None) -> dict:
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload

