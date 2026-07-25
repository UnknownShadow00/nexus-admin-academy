import csv
import io
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.quiz import QuestionImportConfirmRequest
from app.services.admin_auth import verify_admin
from app.services.question_importer import (
    TEMPLATE_COLUMNS,
    ImportFileError,
    confirm_import,
    parse_csv_file,
    parse_xlsx_file,
    preview_rows,
)

router = APIRouter(prefix="/api/admin/quiz/import", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


@router.get("/template")
def download_template():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TEMPLATE_COLUMNS)
    writer.writerow(
        [
            "Networking Fundamentals",
            "multi",
            "Which basic information is typically required when opening a help desk ticket? (Select 3 answers)",
            "User information",
            "Expected resolution date",
            "Device information",
            "Escalation levels required",
            "Problem description",
            "",
            "",
            "",
            "A|C|E",
            "Tickets need requester, device, and problem details up front.",
            "2",
            "help-desk,tickets",
            "Nexus curriculum team",
            "false",
        ]
    )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=question_import_template.csv"},
    )


async def _parse_upload(file: UploadFile) -> list[dict]:
    filename = (file.filename or "").lower()
    data = await file.read()
    if filename.endswith(".csv"):
        return parse_csv_file(data)
    if filename.endswith(".xlsx"):
        return parse_xlsx_file(data)
    if filename.endswith(".xlsm"):
        raise HTTPException(status_code=400, detail="Macro-enabled workbooks (.xlsm) are not accepted.")
    raise HTTPException(status_code=400, detail="Only .csv or .xlsx files are accepted.")


@router.post("/preview")
async def preview_import(file: UploadFile, db: Session = Depends(get_db)):
    try:
        raw_rows = await _parse_upload(file)
    except ImportFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    previewed = preview_rows(db, raw_rows)
    valid_rows = [r for r in previewed if r.valid]
    invalid_rows = [r for r in previewed if not r.valid]

    return {
        "success": True,
        "data": {
            "filename": file.filename,
            "total_rows": len(previewed),
            "valid_count": len(valid_rows),
            "invalid_count": len(invalid_rows),
            "duplicate_count": sum(1 for r in valid_rows if r.is_duplicate),
            "valid_rows": [
                {
                    "row_number": r.row_number,
                    "raw_row": raw_rows[r.row_number - 2],
                    "payload": r.payload,
                    "warnings": r.warnings,
                    "info": r.info,
                    "is_duplicate": r.is_duplicate,
                    "existing_question_id": r.existing_question_id,
                }
                for r in valid_rows
            ],
            "invalid_rows": [
                {
                    "row_number": r.row_number,
                    "raw_row": raw_rows[r.row_number - 2],
                    "errors": r.errors,
                }
                for r in invalid_rows
            ],
        },
    }


@router.post("/preview/error-report")
def download_error_report(invalid_rows: list[dict] = Body(embed=True)):
    """Accepts the client-held list of invalid rows (from the preview
    response) and re-renders it as a downloadable CSV. Stateless — nothing
    is read from or written to the database."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row_number", "errors"])
    for row in invalid_rows:
        writer.writerow([row.get("row_number"), "; ".join(row.get("errors", []))])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=question_import_errors.csv"},
    )


@router.post("/confirm")
def confirm_import_endpoint(payload: QuestionImportConfirmRequest, db: Session = Depends(get_db)):
    try:
        summary = confirm_import(
            db,
            payload.rows,
            duplicate_policy=payload.duplicate_policy,
            source_filename=payload.source_filename or "unknown",
        )
    except Exception as exc:  # noqa: BLE001 — deliberately broad: any failure must roll back and surface
        logger.exception("question_import_confirm_failed filename=%s", payload.source_filename)
        raise HTTPException(status_code=500, detail=f"Import failed and was rolled back: {exc}") from exc

    logger.info(
        "question_import_confirm filename=%s created=%s updated=%s skipped_duplicates=%s skipped_invalid=%s",
        payload.source_filename,
        summary["created"],
        summary["updated"],
        summary["skipped_duplicates"],
        summary["skipped_invalid"],
    )
    return {"success": True, "data": summary}
