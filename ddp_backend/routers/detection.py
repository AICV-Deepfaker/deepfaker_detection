import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlmodel.orm.session import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.security import get_current_user
from ddp_backend.models import User
from ddp_backend.schemas.enums import AnalyzeMode, ModelName, Result, Status
from ddp_backend.schemas.report import (
    DeepReportResponse,
    FastReportResponse,
    STTReport,
    VideoReport,
    ProbabilityContent,
    VisualContent,
    ProbVisualContent
)
from ddp_backend.services.crud import CRUDResult, CRUDVideo
from ddp_backend.task.detection import predict_deepfake_deep, predict_deepfake_fast

router = APIRouter(prefix="/prediction", tags=["prediction"])


# ✅ user_id만 뽑아서 int로 반환 (OpenAPI도 깔끔)
def get_current_user_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    return current_user.user_id


@router.post(path="/{mode}", status_code=status.HTTP_202_ACCEPTED)
async def predict_deepfake(
    video_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    mode: AnalyzeMode,
) -> None:
    video = CRUDVideo.get_by_id(db, video_id)
    if video is None:
        raise HTTPException(404, "Video Not Found")
    if video.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    if mode == AnalyzeMode.FAST:
        await predict_deepfake_fast.kiq(video.video_id)
    elif mode == AnalyzeMode.DEEP:
        await predict_deepfake_deep.kiq(video.video_id)
    return None


@router.get("/status/{video_id}")
async def get_video_status(
    video_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    video = CRUDVideo.get_by_id(db, video_id)
    if video is None:
        raise HTTPException(404, "Video Not Found")
    if video.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    result = CRUDResult.get_by_video_id(db, video_id)
    return {
        "status": video.status,
        "result_id": str(result.result_id) if result is not None else None,
    }


type ResultType = Annotated[
    FastReportResponse | DeepReportResponse, Field(discriminator="analysis_mode")
]


def conf_to_prob(conf: float, result: Result) -> float:
    match result:
        case Result.UNKNOWN:
            return 0.5
        case Result.REAL:
            return conf
        case Result.FAKE:
            return 1 - conf


@router.get(path="/result/{result_id}", response_model=ResultType)
async def get_result(
    result_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    result = CRUDResult.get_by_id(db, result_id)
    if result is None:
        raise HTTPException(404, "Item not found")
    if result.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    if result.is_fast:
        report = result.fast_report
        return FastReportResponse(
            status=Status.SUCCESS if report is not None else Status.ERROR,
            error_msg=None if report is not None else "Could not find detailed report",
            result=result.total_result,
            r_ppg=VideoReport[VisualContent](
                status=Status.SUCCESS,
                model_name=ModelName.R_PPG,
                content=VisualContent(
                    visual_report=report.rppg_image,
                )
            )
            if report is not None
            else None,
            wavelet=VideoReport[ProbVisualContent](
                status=Status.SUCCESS,
                model_name=ModelName.WAVELET,
                content=ProbVisualContent(
                    visual_report=report.freq_image,
                    probability=conf_to_prob(report.freq_conf, report.freq_result),
                )
            )
            if report is not None
            and (
                result.total_result == report.freq_result
                or result.total_result == Result.UNKNOWN
            )
            else None,
            stt=STTReport(
                risk_level=report.stt_risk_level,
                **report.stt_script.model_dump(),
            )
            if report is not None
            else None,
        )
    else:
        report = result.deep_report
        return DeepReportResponse(
            status=Status.SUCCESS if report is not None else Status.ERROR,
            error_msg=None if report is not None else "Could not find detailed report",
            result=result.total_result,
            unite=VideoReport[ProbabilityContent](
                status=Status.SUCCESS,
                model_name=ModelName.UNITE,
                content=ProbabilityContent(
                    probability=conf_to_prob(report.unite_conf, report.unite_result),
                )
            )
            if report is not None
            else None,
        )
