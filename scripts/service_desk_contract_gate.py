#!/usr/bin/env python3
"""Fail-closed semantic contract validation for Nexus Backend and Service Desk."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from typing import NamedTuple
from urllib.request import Request, urlopen


class ContractResult(NamedTuple):
    ok: bool
    detail: str


def _object(payload: str | None, label: str) -> tuple[dict | None, ContractResult | None]:
    if payload is None:
        return None, ContractResult(False, f"{label} contract endpoint is missing")
    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return None, ContractResult(False, f"{label} returned malformed JSON")
    if not isinstance(value, dict):
        return None, ContractResult(False, f"{label} contract response is not an object")
    return value, None


def evaluate_payloads(backend_payload: str | None, service_desk_payload: str | None) -> ContractResult:
    backend, error = _object(backend_payload, "backend")
    if error:
        return error
    service_desk, error = _object(service_desk_payload, "Service Desk")
    if error:
        return error
    assert backend is not None and service_desk is not None

    backend_version = backend.get("contract_version")
    service_desk_version = service_desk.get("contract_version")
    if not isinstance(backend_version, str) or not backend_version.strip():
        return ContractResult(False, "backend contract_version is missing or malformed")
    if not isinstance(service_desk_version, str) or not service_desk_version.strip():
        return ContractResult(False, "Service Desk contract_version is missing or malformed")
    if service_desk.get("status") != "ok":
        return ContractResult(False, f"Service Desk health status is {service_desk.get('status')!r}")
    if backend_version != service_desk_version:
        return ContractResult(
            False,
            f"contract mismatch: backend={backend_version}, Service Desk={service_desk_version}",
        )
    contract = service_desk.get("contract")
    if isinstance(contract, dict) and contract.get("compatible") is False:
        return ContractResult(False, "Service Desk reports backend contract incompatibility")
    return ContractResult(True, f"compatible semantic contract {backend_version}")


def _python_constant(path: str, name: str) -> str | None:
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return value if isinstance(value, str) else None
    return None


def evaluate_candidate_source(repo_root: str) -> ContractResult:
    backend_path = os.path.join(repo_root, "backend", "app", "services", "service_desk_contract.py")
    web_path = os.path.join(repo_root, "service-desk-app", "apps", "web", "lib", "service-desk-contract.ts")
    health_path = os.path.join(repo_root, "service-desk-app", "apps", "web", "app", "api", "health", "route.ts")
    try:
        backend_version = _python_constant(backend_path, "SERVICE_DESK_CONTRACT_VERSION")
        web_source = open(web_path, encoding="utf-8").read()
        health_source = open(health_path, encoding="utf-8").read()
    except (OSError, SyntaxError, ValueError) as exc:
        return ContractResult(False, f"candidate contract metadata is unreadable: {exc}")
    match = re.search(
        r"EXPECTED_NEXUS_SERVICE_DESK_CONTRACT\s*=\s*['\"]([^'\"]+)['\"]",
        web_source,
    )
    web_version = match.group(1) if match else None
    if not backend_version or not web_version:
        return ContractResult(False, "candidate contract constant is missing or malformed")
    if "contract_version: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT" not in health_source:
        return ContractResult(False, "candidate Service Desk health contract field is missing")
    if backend_version != web_version:
        return ContractResult(
            False,
            f"candidate contract mismatch: backend={backend_version}, Service Desk={web_version}",
        )
    return ContractResult(True, f"candidate semantic contract {backend_version}")


def fetch_payload(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "nexus-contract-gate/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def evaluate_urls(backend_url: str, service_desk_url: str, timeout: float = 5.0) -> ContractResult:
    try:
        backend = fetch_payload(backend_url.rstrip("/") + "/api/service-desk/contract", timeout)
    except Exception as exc:
        return ContractResult(False, f"backend contract endpoint unavailable: {exc}")
    try:
        service_desk = fetch_payload(
            service_desk_url.rstrip("/") + "/service-desk/api/health", timeout
        )
    except Exception as exc:
        return ContractResult(False, f"Service Desk contract endpoint unavailable: {exc}")
    return evaluate_payloads(backend, service_desk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-json")
    parser.add_argument("--service-desk-json")
    parser.add_argument("--backend-url")
    parser.add_argument("--service-desk-url")
    parser.add_argument("--candidate-root")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if args.candidate_root:
        result = evaluate_candidate_source(os.path.abspath(args.candidate_root))
    elif args.backend_url and args.service_desk_url:
        result = evaluate_urls(args.backend_url, args.service_desk_url, args.timeout)
    else:
        result = evaluate_payloads(args.backend_json, args.service_desk_json)
    print(result.detail)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
