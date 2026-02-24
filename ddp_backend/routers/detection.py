from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import Field
from sqlmodel.orm.session import Session

from ddp_backend.core.database import get_db
from ddp_backend.core.s3 import upload_video_to_s3
from ddp_backend.core.security import get_current_user
from ddp_backend.models import Source, Video
from ddp_backend.schemas.api import APIOutputDeep, APIOutputFast
from ddp_backend.schemas.enums import AnalyzeMode, ModelName, OriginPath, Result, Status
from ddp_backend.schemas.report import STTReport, VideoReport
from ddp_backend.schemas.user import UserRead
from ddp_backend.services.crud import CRUDResult, CRUDVideo
from ddp_backend.services.crud.source import CRUDSource
from ddp_backend.task.detection import predict_deepfake_deep, predict_deepfake_fast

router = APIRouter(prefix="/prediction", tags=["prediction"])


# ✅ user_id만 뽑아서 int로 반환 (OpenAPI도 깔끔)
def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.user_id


@router.post(path="/{mode}", status_code=status.HTTP_202_ACCEPTED)
async def predict_deepfake(
    file: Annotated[UploadFile, File(...)],
    user: Annotated[
        UserRead, Depends(get_current_user)
    ],  # TODO add dependency gives user id from JWT token
    db: Annotated[Session, Depends(get_db)],
    mode: AnalyzeMode,
) -> None:
    user_id = user.user_id
    video = CRUDVideo.create(
        db,
        Video(
            user_id=user_id,
            origin_path=OriginPath.UPLOAD,
        ),
    )
    filename = file.filename if file.filename is not None else "unnamed.mp4"
    s3_path = upload_video_to_s3(file.file, filename)
    CRUDSource.create(
        db,
        Source(
            video_id=video.video_id,
            s3_path=s3_path,
        ),
    )
    if mode == AnalyzeMode.FAST:
        await predict_deepfake_fast.kiq(video.video_id)
    elif mode == AnalyzeMode.DEEP:
        await predict_deepfake_deep.kiq(video.video_id)
    return None


type ResultType = Annotated[
    APIOutputFast | APIOutputDeep, Field(discriminator="analysis_mode")
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
    result_id: int,
    user: Annotated[UserRead, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    result = CRUDResult.get_by_id(db, result_id)
    if result is None:
        raise HTTPException(404, "Item not found")
    if result.user_id != user.user_id:
        raise HTTPException(403, "Forbidden")

    if result.is_fast:
        report = result.fast_report
        return APIOutputFast(
            status=Status.SUCCESS if report is not None else Status.ERROR,
            error_msg=None if report is not None else "Could not find detailed report",
            result=result.total_result,
            r_ppg=VideoReport(
                status=Status.SUCCESS,
                model_name=ModelName.R_PPG,
                result=report.rppg_result,
                probability=conf_to_prob(report.rppg_conf, report.rppg_result),
                visual_report=report.rppg_image,
            )
            if report is not None
            else None,
            wavelet=VideoReport(
                status=Status.SUCCESS,
                model_name=ModelName.WAVELET,
                result=report.freq_result,
                probability=conf_to_prob(report.freq_conf, report.freq_result),
                visual_report=report.freq_image,
            )
            if report is not None
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
        return APIOutputDeep(
            status=Status.SUCCESS if report is not None else Status.ERROR,
            error_msg=None if report is not None else "Could not find detailed report",
            result=result.total_result,
            unite=VideoReport(
                status=Status.SUCCESS,
                model_name=ModelName.UNITE,
                result=report.unite_result,
                probability=conf_to_prob(report.unite_conf, report.unite_result),
                visual_report="",
            )
            if report is not None
            else None,
        )
