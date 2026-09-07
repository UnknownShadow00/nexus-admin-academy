"""Generate the V2 Service Desk assessment integrity inventory.

This script is intentionally scratch-database only.  It loads the same V2
foundation used by the application, then records the grading-profile and
browser-fixture compatibility of every Service Desk module assessment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _require_scratch_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("sqlite:////tmp/"):
        raise SystemExit("DATABASE_URL must be an explicit /tmp scratch sqlite path")
    if database_url.endswith("/backend/nexus.db") or database_url.endswith("/nexus.db"):
        raise SystemExit("Refusing to use the production backend/nexus.db")
    if database_url == "sqlite:///:memory:":
        raise SystemExit("Use a visible file-backed scratch sqlite DATABASE_URL")
    return database_url


# app.database binds its engine during the model imports below. For direct CLI
# execution, reject an unsafe target before those imports can occur.
if __name__ == "__main__":
    _require_scratch_database_url()

from app.models.certification import (  # noqa: E402
    CertificationModule,
    CertificationVersion,
    ModuleAssessment,
)
from app.models.service_desk import (  # noqa: E402
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.services.service_desk_objectives import objective_definition  # noqa: E402
from app.services.v2_access import v2_master_enabled  # noqa: E402

DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs/service_desk_v2_assessment_inventory.md"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "docs/service_desk_v2_assessment_inventory.json"


@dataclass(frozen=True)
class InventoryRow:
    module: str
    assessment_key: str
    scenario_stable_key: str
    catalog_version: str
    process_profile: bool
    grading_categories: tuple[str, ...]
    browser_operable: bool
    student_visible: bool
    ticket_id: str
    asset_tag: str


def _browser_catalogs() -> tuple[set[str], set[str]]:
    """Read the fixture identities used by the browser simulation engine."""
    ticket_source = (
        REPO_ROOT / "service-desk-app/packages/shared/src/ticket-fixtures.ts"
    ).read_text(encoding="utf-8")
    remote_source = (
        REPO_ROOT
        / "service-desk-app/packages/shared/src/remote-desktop-fixtures.ts"
    ).read_text(encoding="utf-8")
    ticket_ids = set(re.findall(r"\bid:\s*['\"](INC\d+)['\"]", ticket_source))
    asset_tags = set(re.findall(r"['\"](NX-[A-Z0-9-]+)['\"]", remote_source))
    return ticket_ids, asset_tags


def collect_inventory(db, *, feature_enabled: bool | None = None) -> list[InventoryRow]:
    """Return one deterministic row per V2 Service Desk module assessment."""
    ticket_ids, asset_tags = _browser_catalogs()
    enabled = v2_master_enabled() if feature_enabled is None else feature_enabled
    rows = (
        db.query(
            ModuleAssessment,
            CertificationModule,
            CertificationVersion,
            ServiceDeskScenario,
        )
        .join(
            CertificationModule,
            CertificationModule.id == ModuleAssessment.certification_module_id,
        )
        .join(
            CertificationVersion,
            CertificationVersion.id == CertificationModule.certification_version_id,
        )
        .outerjoin(
            ServiceDeskScenario,
            ServiceDeskScenario.id == ModuleAssessment.service_desk_scenario_id,
        )
        .filter(ModuleAssessment.assessment_role == "service_desk")
        .order_by(CertificationModule.module_key, ModuleAssessment.assessment_key)
        .all()
    )

    inventory: list[InventoryRow] = []
    for assessment, module, cert_version, scenario in rows:
        version = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(
                scenario_id=scenario.id if scenario else -1,
                status="published",
            )
            .order_by(
                ServiceDeskScenarioVersion.version_number.desc(),
                ServiceDeskScenarioVersion.id.desc(),
            )
            .first()
        )
        definition = version.definition_json if version else {}
        stable_key = scenario.stable_key if scenario else "unresolved"
        objective = objective_definition(stable_key, definition) if scenario else None
        categories = tuple(category.name for category in objective.categories) if objective else ()
        ticket_id = str(definition.get("id") or "")
        device = definition.get("device") if isinstance(definition.get("device"), dict) else {}
        asset_tag = str(device.get("assetTag") or "")
        browser_operable = ticket_id in ticket_ids and asset_tag in asset_tags
        student_visible = bool(
            enabled
            and assessment.active
            and module.active
            # CertificationVersion has no separate publication-status column;
            # active is the loader/runtime publication gate for this model.
            and cert_version.active
            and scenario
            and scenario.status == "active"
            and version
        )
        inventory.append(
            InventoryRow(
                module=module.module_key,
                assessment_key=assessment.assessment_key,
                scenario_stable_key=stable_key,
                catalog_version=str(definition.get("objective_catalog_version") or "none"),
                process_profile=bool(objective and objective.is_process_profile),
                grading_categories=categories,
                browser_operable=browser_operable,
                student_visible=student_visible,
                ticket_id=ticket_id,
                asset_tag=asset_tag,
            )
        )
    return inventory


def wave2_invariant_failures(rows: list[InventoryRow]) -> list[str]:
    """Rows that would be unsafe to expose when the V2 feature flag is enabled."""
    return sorted(
        row.assessment_key
        for row in rows
        if not row.process_profile or not row.grading_categories
    )


def browser_operability_failures(rows: list[InventoryRow]) -> list[str]:
    return sorted(row.assessment_key for row in rows if not row.browser_operable)


def note_only_assessments(rows: list[InventoryRow]) -> list[str]:
    return sorted(
        row.assessment_key
        for row in rows
        if row.catalog_version == "none" and not row.grading_categories
    )


def render_markdown(rows: list[InventoryRow], *, feature_enabled: bool) -> str:
    flag_state = "enabled" if feature_enabled else "disabled"
    counts = {
        "note-only": len(note_only_assessments(rows)),
        "process-v3": sum(row.catalog_version == "process-v3" for row in rows),
        "realism-v1": sum(row.catalog_version == "realism-v1" for row in rows),
        "realism-v2": sum(row.catalog_version == "realism-v2" for row in rows),
    }
    lines = [
        "# Nexus V2 Service Desk assessment inventory",
        "",
        "Generated by `backend/scripts/generate_service_desk_v2_inventory.py` from a scratch-only V2 content load.",
        "",
        f"V2 feature flag: **{flag_state}** (`V2_CURRICULUM_ENABLED`). Student-visible includes this flag plus active assessment/module/scenario, an active certification version (the model's publication gate), and a published scenario version.",
        "",
        "| module | assessment key | scenario stable_key | catalog version | process profile? | grading categories | browser-operable | student-visible |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        categories = ", ".join(row.grading_categories)
        visible = "yes (V2 flag on)" if row.student_visible else f"no (V2 flag {flag_state})"
        lines.append(
            f"| {row.module} | {row.assessment_key} | {row.scenario_stable_key} | "
            f"{row.catalog_version} | {'yes' if row.process_profile else 'no'} | "
            f"{categories} | {'yes' if row.browser_operable else 'no'} | {visible} |"
        )
    invariant_failures = wave2_invariant_failures(rows)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Total Service Desk assessments: {len(rows)}",
            f"- Note-only: {counts['note-only']}",
            f"- process-v3: {counts['process-v3']}",
            f"- realism-v1: {counts['realism-v1']}",
            f"- realism-v2: {counts['realism-v2']}",
            f"- Browser-operability failures: {len(browser_operability_failures(rows))}",
            "",
            "## Wave-2 invariant failures",
            "",
            "These assessments would violate `no V2 student-available Service Desk assessment may have process_weights null or empty grading categories` if V2 were enabled:",
            "",
            *[f"- `{key}`" for key in invariant_failures],
            "",
        ]
    )
    return "\n".join(lines)


def render_json(rows: list[InventoryRow], *, feature_enabled: bool) -> str:
    payload = {
        "feature_flag": {
            "name": "V2_CURRICULUM_ENABLED",
            "enabled": feature_enabled,
        },
        "rows": [
            {**asdict(row), "grading_categories": list(row.grading_categories)}
            for row in rows
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    args = parser.parse_args()

    database_url = _require_scratch_database_url()
    print(f"DATABASE_URL={database_url}")

    # The top-level CLI guard ran before app.database bound its engine. Print
    # the selected scratch path again here so every generated artifact run is
    # auditable in command output.
    import app.models  # noqa: F401
    import seed_v2_foundation
    from app.database import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_v2_foundation.run(db)
        enabled = v2_master_enabled()
        rows = collect_inventory(db, feature_enabled=enabled)

    markdown = render_markdown(rows, feature_enabled=enabled)
    json_text = render_json(rows, feature_enabled=enabled)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    args.json_output.write_text(json_text, encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output}")
    print(f"Wrote browser fixture data to {args.json_output}")
    print(
        "Summary: "
        f"note-only={len(note_only_assessments(rows))} "
        f"process-v3={sum(row.catalog_version == 'process-v3' for row in rows)} "
        f"realism-v1={sum(row.catalog_version == 'realism-v1' for row in rows)} "
        f"realism-v2={sum(row.catalog_version == 'realism-v2' for row in rows)}"
    )
    print("Wave-2 invariant failures: " + ", ".join(wave2_invariant_failures(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
