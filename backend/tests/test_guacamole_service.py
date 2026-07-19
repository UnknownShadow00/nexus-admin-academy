import json

import httpx

from app.services import guacamole_service


def _configure(monkeypatch):
    monkeypatch.setenv("GUACAMOLE_URL", "https://guac.example/guacamole")
    monkeypatch.setenv("GUACAMOLE_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("GUACAMOLE_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("GUACAMOLE_DATASOURCE", "postgresql")


def test_client_identifier_matches_guacamole_1_6_format():
    assert guacamole_service.encode_client_identifier("42", "postgresql") == "NDIAYwBwb3N0Z3Jlc3Fs"
    assert "=" not in guacamole_service.encode_client_identifier("42", "postgresql")


def test_scoped_access_uses_temporary_user_and_only_connection_read(monkeypatch):
    _configure(monkeypatch)
    requests = []
    auth_calls = 0

    def handler(request):
        nonlocal auth_calls
        requests.append(request)
        if request.url.path.endswith("/api/tokens"):
            auth_calls += 1
            return httpx.Response(200, json={"authToken": "admin-token" if auth_calls == 1 else "student-token"})
        if request.method == "POST" and request.url.path.endswith("/users"):
            return httpx.Response(201, json={})
        if request.method == "PATCH" and request.url.path.endswith("/permissions"):
            return httpx.Response(204)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(guacamole_service, "_CLIENT", client)
    monkeypatch.setattr(guacamole_service.secrets, "token_hex", lambda _: "0011223344556677")
    monkeypatch.setattr(guacamole_service.secrets, "token_urlsafe", lambda _: "random-password")

    access = guacamole_service.create_scoped_access("connection-A", 71)

    assert access["username"] == "lab-71-0011223344556677"
    assert "student-token" in access["url"]
    assert "admin-token" not in access["url"]
    user_payload = json.loads(next(r for r in requests if r.method == "POST" and r.url.path.endswith("/users")).content)
    assert user_payload["password"] == "random-password"
    patch_payload = json.loads(next(r for r in requests if r.method == "PATCH").content)
    assert patch_payload == [{
        "op": "add",
        "path": "/connectionPermissions/connection-A",
        "value": "READ",
    }]
    assert all("systemPermissions" not in r.content.decode(errors="ignore") for r in requests)

