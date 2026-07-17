import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.cli_lab import CliLab


BACKEND_CLI_LAB_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cli_labs"
FRONTEND_CLI_LAB_DATA_DIR = Path(__file__).resolve().parents[3] / "frontend" / "src" / "features" / "cli-labs" / "data" / "lessons"


def _lesson_paths() -> list[Path]:
    backend_paths = sorted(BACKEND_CLI_LAB_DATA_DIR.glob("*.json")) if BACKEND_CLI_LAB_DATA_DIR.exists() else []
    if backend_paths:
        return backend_paths
    return sorted(FRONTEND_CLI_LAB_DATA_DIR.glob("*.json")) if FRONTEND_CLI_LAB_DATA_DIR.exists() else []


def seed_cli_labs(db: Session) -> None:
    for path in _lesson_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        compartment_id = payload["compartmentId"]
        vendor_id = payload["vendorId"]
        shared_topology = payload.get("sharedTopology") or {}

        for index, lesson in enumerate(payload.get("lessons", []), start=1):
            content = dict(lesson)
            content.setdefault("compartmentId", compartment_id)
            content.setdefault("vendorId", vendor_id)
            content.setdefault("topology", shared_topology)

            lab = db.query(CliLab).filter(CliLab.id == lesson["id"]).first()
            fields = {
                "compartment_id": compartment_id,
                "vendor_id": vendor_id,
                "title": lesson["title"],
                "difficulty": lesson.get("difficulty", "Beginner"),
                "est_minutes": lesson.get("estimatedMinutes"),
                "order_index": index,
                "content": content,
            }
            if lab is None:
                db.add(CliLab(id=lesson["id"], **fields))
            else:
                for key, value in fields.items():
                    setattr(lab, key, value)
