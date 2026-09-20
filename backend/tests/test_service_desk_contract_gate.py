"""Fail-closed semantic contract checks shared by operator tooling."""

import importlib.util
import os

import pytest


SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "service_desk_contract_gate.py")
)
spec = importlib.util.spec_from_file_location("service_desk_contract_gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gate)


@pytest.mark.parametrize(
    "backend,service_desk,ok,reason",
    [
        (
            '{"contract_version":"2.0"}',
            '{"status":"ok","contract_version":"2.0"}',
            True,
            "compatible",
        ),
        (None, '{"status":"ok","contract_version":"2.0"}', False, "backend"),
        ('{"contract_version":"2.0"}', '{"status":"ok"}', False, "missing"),
        (
            '{"contract_version":"2.0"}',
            '{"status":"ok","contract_version":"1.7"}',
            False,
            "mismatch",
        ),
        ('not-json', '{"status":"ok","contract_version":"2.0"}', False, "malformed"),
        (
            '{"contract_version":"2.0"}',
            '{"status":"ok","contract_version":"1.0"}',
            False,
            "mismatch",
        ),
    ],
)
def test_contract_payload_matrix(backend, service_desk, ok, reason):
    result = gate.evaluate_payloads(backend, service_desk)
    assert result.ok is ok
    assert reason in result.detail.lower()


def test_service_desk_reported_mismatch_fails_even_when_versions_match():
    result = gate.evaluate_payloads(
        '{"contract_version":"2.0"}',
        '{"status":"contract_mismatch","contract_version":"2.0"}',
    )
    assert result.ok is False
    assert "status" in result.detail.lower()
