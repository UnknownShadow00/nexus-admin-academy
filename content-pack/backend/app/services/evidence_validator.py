import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.evidence import EvidenceArtifact

MAX_FILE_SIZE = 5 * 1024 * 1024

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except Exception:  # pragma: no cover
    Image = None
    TAGS = {}


def validate_evidence_artifact(
    *,
    file_path: str,
    artifact_type: str,
    validation_rules: dict,
    db: Session,
) -> dict:
    issues: list[str] = []
    metadata: dict = {}
    path = Path(file_path)

    if not path.exists():
        return {"valid": False, "issues": ["File missing"], "metadata": {}, "checksum": ""}

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        issues.append(f"File too large: {file_size / 1024 / 1024:.2f}MB")

    checksum = _sha256(file_path)
    duplicate = db.query(EvidenceArtifact).filter(EvidenceArtifact.checksum == checksum).first()
    if duplicate:
        issues.append(f"Duplicate checksum already uploaded at {duplicate.uploaded_at}")

    if artifact_type == "screenshot":
        metadata = _extract_screenshot_metadata(file_path)
        timestamp = metadata.get("timestamp")
        if timestamp:
            try:
                parsed = _parse_timestamp(timestamp)
                if parsed and datetime.now() - parsed > timedelta(days=7):
                    issues.append(f"Screenshot too old: {timestamp}")
            except Exception:
                pass

        software = (metadata.get("software") or "").lower()
        if any(tool in software for tool in ["photoshop", "gimp", "paint.net"]):
            issues.append("Possible edited image detected from metadata software field")

    if artifact_type == "log":
        must_contain = validation_rules.get("must_contain_text", [])
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""
        for required_text in must_contain:
            if required_text not in content:
                issues.append(f"Missing required text: '{required_text}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "metadata": metadata,
        "checksum": checksum,
    }


def _sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _extract_screenshot_metadata(file_path: str) -> dict:
    if Image is None:
        return {}
    try:
        image = Image.open(file_path)
        exif = image.getexif() or {}
        meta = {}
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            meta[str(tag)] = str(value)
        return {
            "timestamp": meta.get("DateTime") or meta.get("DateTimeOriginal"),
            "software": meta.get("Software"),
            "dimensions": f"{image.width}x{image.height}",
        }
    except Exception:
        return {}


def _parse_timestamp(raw: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None

