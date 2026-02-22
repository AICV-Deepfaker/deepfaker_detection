from typing import Annotated

from fastapi import APIRouter, File, UploadFile, Depends
from sqlalchemy.orm import Session

from ddp_backend.schemas.api import (
    APIOutputDeep,
    APIOutputFast,
)
from ddp_backend.schemas.report import STTScript
from ddp_backend.services.dependencies import detection_pipeline
from ddp_backend.utils.file_handler import save_temp_file
from ddp_backend.services.crud import FastReportCreate, DeepReportCreate, CRUDFastReport, CRUDDeepReport
from ddp_backend.core.database import get_db


router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.post(path="/fast")
def predict_deepfake_fast(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)]
) -> APIOutputFast:
    with save_temp_file(file) as temp_path:
        output = detection_pipeline.run_fast_mode(temp_path)
        assert output.wavelet is not None and output.r_ppg is not None and output.stt is not None
        CRUDFastReport.create(db, FastReportCreate(
            user_id=...,
            result_id=...,
            freq_result=output.wavelet.result,
            freq_conf=output.wavelet.confidence_score,
            freq_image=output.wavelet.visual_report,
            rppg_result=output.r_ppg.result,
            rppg_conf=output.r_ppg.confidence_score,
            rppg_image=output.r_ppg.visual_report,
            stt_keyword=output.stt.keywords,
            stt_risk_level=output.stt.risk_level,
            stt_script=STTScript(
                risk_reason=output.stt.risk_reason,
                transcript=output.stt.transcript,
                search_results=output.stt.search_results,
            )
        ))
        return output


@router.post("/deep")
def predict_deepfake_deep(
    file: Annotated[UploadFile, File(...)],
) -> APIOutputDeep:
    with save_temp_file(file) as temp_path:
        return detection_pipeline.run_deep_mode(temp_path)
