import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from redis import Redis
from sqlmodel.orm.session import Session
from taskiq import TaskiqDepends

from ddp_backend.core.database import get_db
from ddp_backend.core.model import detection_pipeline
from ddp_backend.core.redis_bridge import NOTIFY_CHANNEL, REDIS_URL
from ddp_backend.core.s3 import download_video_from_s3
from ddp_backend.core.tk_broker import broker
from ddp_backend.models import DeepReport, FastReport, Result
from ddp_backend.schemas.message import WorkerResultMessage
from ddp_backend.schemas.enums import VideoStatus
from ddp_backend.services.crud import (
    CRUDDeepReport,
    CRUDFastReport,
    CRUDResult,
    CRUDSource,
    CRUDVideo,
)

_redis = Redis.from_url(REDIS_URL if REDIS_URL is not None else "")


def publish_notification(msg: WorkerResultMessage):
    _redis.publish(NOTIFY_CHANNEL, msg.model_dump_json())


@broker.task
def predict_deepfake_fast(
    video_id: uuid.UUID,
    db: Session = TaskiqDepends(get_db),
) -> uuid.UUID | None:
    src = CRUDSource.get_by_video(db, video_id)
    if src is None:
        return None

    with TemporaryDirectory() as temp_dir:
        temp_path = download_video_from_s3(src.s3_path, Path(temp_dir))
        CRUDVideo.update_status(db, src.video_id, VideoStatus.PROCESSING)

        output = detection_pipeline.run_fast_mode(temp_path)

        if output is None:
            CRUDVideo.update_status(db, src.video_id, VideoStatus.FAILED)
            return None

        """
        total_result: ResultEnum
        if output.freq_conf > output.rppg_conf:
            total_result = output.freq_result
        elif output.freq_conf < output.rppg_conf:
            total_result = output.rppg_result
        else:
            total_result = ResultEnum.UNKNOWN
        """
        total_result = output.freq_result

        result = CRUDResult.create(
            db,
            Result(
                user_id=src.video.user_id,
                video_id=src.video.video_id,
                total_result=total_result,
                is_fast=True,
            ),
        )
        CRUDFastReport.create(
            db,
            FastReport(
                user_id=src.video.user_id,
                result_id=result.result_id,
                **output.model_dump()
            ),
        )
        CRUDVideo.update_status(db, src.video_id, VideoStatus.COMPLETED)
        publish_notification(
            WorkerResultMessage(
                user_id=src.video.user_id,
                result_id=result.result_id,
            )
        )
        return result.result_id


@broker.task()
def predict_deepfake_deep(
    video_id: uuid.UUID,
    db: Session = TaskiqDepends(get_db),
) -> uuid.UUID | None:
    src = CRUDSource.get_by_video(db, video_id)
    if src is None:
        return None

    with TemporaryDirectory() as temp_dir:
        temp_path = download_video_from_s3(src.s3_path, Path(temp_dir))
        CRUDVideo.update_status(db, src.video_id, VideoStatus.PROCESSING)

        output = detection_pipeline.run_deep_mode(temp_path)

        if output is None:
            CRUDVideo.update_status(db, src.video_id, VideoStatus.FAILED)
            return None

        result = CRUDResult.create(
            db,
            Result(
                user_id=src.video.user_id,
                video_id=src.video.video_id,
                total_result=output.unite_result,
                is_fast=False,
            ),
        )
        CRUDDeepReport.create(
            db,
            DeepReport(
                user_id=src.video.user_id,
                result_id=result.result_id,
                **output.model_dump()
            ),
        )
        CRUDVideo.update_status(db, src.video_id, VideoStatus.COMPLETED)
        publish_notification(
            WorkerResultMessage(
                user_id=src.video.user_id,
                result_id=result.result_id,
            )
        )
        return result.result_id
