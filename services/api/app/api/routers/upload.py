"""Upload ДЗК + ДРРП file pair and ingest into a new dataset."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, session_dep
from app.api.envelope import ApiResponse, ok
from app.api.errors import ValidationError
from app.api.schemas import (
    UploadResponse,
    ValidationIssueDTO,
    WorkbookValidationDTO,
)
from app.ingest.service import ingest_dataset
from app.ingest.validation import (
    SUPPORTED_EXTENSIONS,
    ValidationErrorSummary,
    validate_input_file,
)
from app.security.audit import log_action
from app.security.auth import Principal

router = APIRouter(prefix="/api/upload", tags=["upload"])


_ACCEPTED_EXT_DESCRIPTION = (
    "Accepted extensions: " + ", ".join(sorted(SUPPORTED_EXTENSIONS))
)


def _save_temp(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "").suffix or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(upload.file, tmp)
    finally:
        tmp.close()
    return Path(tmp.name)


def _prevalidate(upload: UploadFile, role: str) -> None:
    if not upload.filename:
        raise ValidationError(f"{role} file is required (missing filename).")
    try:
        validate_input_file(
            upload.file,
            filename=upload.filename,
            content_type=upload.content_type,
        )
    except ValidationErrorSummary as exc:
        raise ValidationError(
            f"[{role}] {exc.message}",
            details={"code": exc.code, "role": role, **exc.details},
        ) from exc
    finally:
        # validate_input_file already rewinds, but guard against any
        # partially-consumed stream so the later temp-file save starts at 0.
        try:
            upload.file.seek(0)
        except Exception:
            pass


def _as_workbook_validation(report: dict) -> WorkbookValidationDTO:
    return WorkbookValidationDTO(
        detected_format=str(report.get("detected_format", "unknown")),
        file_extension=report.get("file_extension"),
        mime_type=report.get("mime_type"),
        source_format=report.get("source_format"),
        present_columns=list(report.get("present_columns", [])),
        unexpected_columns=list(report.get("unexpected_columns", [])),
        issues=[ValidationIssueDTO(**issue) for issue in report.get("issues", [])],
    )


@router.post("", response_model=ApiResponse[UploadResponse])
async def upload_dataset(
    zem: UploadFile = File(..., description=f"ДЗК file. {_ACCEPTED_EXT_DESCRIPTION}"),
    ner: UploadFile = File(..., description=f"ДРРП file. {_ACCEPTED_EXT_DESCRIPTION}"),
    label: str = Form(..., min_length=1, max_length=200),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[UploadResponse]:
    _prevalidate(zem, role="zem")
    _prevalidate(ner, role="ner")

    zem_path = _save_temp(zem)
    ner_path = _save_temp(ner)
    try:
        try:
            result = ingest_dataset(
                session,
                zem_path=zem_path,
                ner_path=ner_path,
                label=label,
                uploaded_by=principal.subject,
                zem_content_type=zem.content_type,
                ner_content_type=ner.content_type,
            )
        except ValidationErrorSummary as exc:
            session.rollback()
            raise ValidationError(
                exc.message,
                details={"code": exc.code, **exc.details},
            ) from exc
        log_action(
            session,
            actor=principal.subject,
            action="upload_dataset",
            target_table="dataset",
            target_id=str(result.dataset_id),
            payload={"label": label, "zem_rows": result.zem_rows, "ner_rows": result.ner_rows},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        zem_path.unlink(missing_ok=True)
        ner_path.unlink(missing_ok=True)

    validation_dto = {
        key: _as_workbook_validation(report) for key, report in result.reports.items()
    }

    return ok(
        UploadResponse(
            dataset_id=result.dataset_id,
            label=label,
            zem_rows=result.zem_rows,
            ner_rows=result.ner_rows,
            persons=result.persons,
            warnings=list(result.warnings),
            validation=validation_dto,
        )
    )
