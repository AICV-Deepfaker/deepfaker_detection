# from typing import Annotated

# from fastapi import APIRouter, File, UploadFile, Depends, status
# from sqlalchemy.orm import Session

# from ddp_backend.schemas.enums import OriginPath, AnalyzeMode
# from ddp_backend.services.crud.source import CRUDSource, SourceCreate
# from ddp_backend.services.crud import CRUDVideo, VideoCreate
# from ddp_backend.core.database import get_db
# from ddp_backend.core.s3 import upload_video_to_s3
# from ddp_backend.task.detection import predict_deepfake_deep, predict_deepfake_fast


# router = APIRouter(prefix="/prediction", tags=["prediction"])


# @router.post(path="/{mode}", status_code=status.HTTP_202_ACCEPTED)
# async def predict_deepfake(
#     file: Annotated[UploadFile, File(...)],
#     user_id: Annotated[
#         int, Depends()
#     ],  # TODO add dependency gives user id from JWT token
#     db: Annotated[Session, Depends(get_db)],
#     mode: AnalyzeMode,
# ) -> None:
#     video = CRUDVideo.create(
#         db,
#         VideoCreate(
#             user_id=user_id,
#             origin_path=OriginPath.UPLOAD,
#         ),
#     )
#     filename = file.filename if file.filename is not None else "unnamed.mp4"
#     s3_path = upload_video_to_s3(file.file, filename)
#     CRUDSource.create(
#         db,
#         SourceCreate(
#             video_id=video.video_id,
#             s3_path=s3_path,
#         ),
#     )
#     if mode == AnalyzeMode.FAST:
#         await predict_deepfake_fast.kiq(video.video_id)
#     elif mode == AnalyzeMode.DEEP:
#         await predict_deepfake_deep.kiq(video.video_id)
#     return None
from fastapi import APIRouter, File, UploadFile, Depends, status, Path, HTTPException
from sqlalchemy.orm import Session

from ddp_backend.schemas.enums import OriginPath, AnalyzeMode
from ddp_backend.services.crud.source import CRUDSource, SourceCreate
from ddp_backend.services.crud import CRUDVideo, VideoCreate
from ddp_backend.core.database import get_db
from ddp_backend.core.s3 import upload_video_to_s3
from ddp_backend.task.detection import predict_deepfake_deep, predict_deepfake_fast

# ✅ 이거 추가: user_id 뽑는 의존성
from ddp_backend.core.security import get_current_user
from ddp_backend.models import User


router = APIRouter(prefix="/prediction", tags=["prediction"])


# ✅ user_id만 뽑아서 int로 반환 (OpenAPI도 깔끔)
def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.user_id


@router.post(path="/{mode}", status_code=status.HTTP_202_ACCEPTED)
async def predict_deepfake(
    mode: AnalyzeMode = Path(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> None:
    # (선택) wavelet FAST가 꺼져있으면 FAST 막기
    if mode == AnalyzeMode.FAST:
        raise HTTPException(status_code=503, detail="FAST model disabled (checkpoint missing). Use DEEP.")

    video = CRUDVideo.create(
        db,
        VideoCreate(
            user_id=user_id,
            origin_path=OriginPath.UPLOAD,
        ),
    )
    filename = file.filename if file.filename is not None else "unnamed.mp4"
    s3_path = upload_video_to_s3(file.file, filename)

    CRUDSource.create(
        db,
        SourceCreate(
            video_id=video.video_id,
            s3_path=s3_path,
        ),
    )

    if mode == AnalyzeMode.DEEP:
        await predict_deepfake_deep.kiq(video.video_id)

    return None