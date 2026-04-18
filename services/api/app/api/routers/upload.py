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
from app.api.schemas import UploadResponse
from app.ingest.service import ingest_dataset
from app.security.auth import Principal
from app.security.audit import log_action

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _save_temp(upload: UploadFile, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(upload.file, tmp)
    finally:
        tmp.close()
    return Path(tmp.name)


@router.post("", response_model=ApiResponse[UploadResponse])
async def upload_dataset(
    zem: UploadFile = File(..., description="ДЗК xlsx"),
    ner: UploadFile = File(..., description="ДРРП xlsx"),
    label: str = Form(..., min_length=1, max_length=200),
    principal: Principal = Depends(require_analyst),
    session: Session = Depends(session_dep),
) -> ApiResponse[UploadResponse]:
    if not zem.filename or not ner.filename:
        raise ValidationError("Both files are required")
    if not zem.filename.lower().endswith(".xlsx") or not ner.filename.lower().endswith(".xlsx"):
        raise ValidationError("Expected .xlsx files")

    zem_path = _save_temp(zem, ".xlsx")
    ner_path = _save_temp(ner, ".xlsx")
    try:
        result = ingest_dataset(
            session,
            zem_path=zem_path,
            ner_path=ner_path,
            label=label,
            uploaded_by=principal.subject,
        )
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

    return ok(
        UploadResponse(
            dataset_id=result.dataset_id,
            label=label,
            zem_rows=result.zem_rows,
            ner_rows=result.ner_rows,
            persons=result.persons,
        )
    )
