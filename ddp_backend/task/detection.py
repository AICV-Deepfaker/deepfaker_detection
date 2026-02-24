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
from ddp_backend.schemas.api import WorkerPubSubAPI
from ddp_backend.schemas.enums import Status, VideoStatus
from ddp_backend.schemas.report import STTScript
from ddp_backend.services.crud import (
    CRUDDeepReport,
    CRUDFastReport,
    CRUDResult,
    CRUDSource,
    CRUDVideo,
)

_redis = Redis.from_url(REDIS_URL if REDIS_URL is not None else "", db=1)


def publish_notification(msg: WorkerPubSubAPI):
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

        if output.wavelet is None or output.r_ppg is None or output.stt is None:
            assert output.status == Status.ERROR
            CRUDVideo.update_status(db, src.video_id, VideoStatus.FAILED)
            return None

        result = CRUDResult.create(
            db,
            Result(
                user_id=src.video.user_id,
                video_id=src.video.video_id,
                total_result=output.result,
                is_fast=True,
            ),
        )
        CRUDFastReport.create(
            db,
            FastReport(
                user_id=src.video.user_id,
                result_id=result.result_id,
                freq_result=output.wavelet.result,
                freq_conf=output.wavelet.confidence_score,
                freq_image=output.wavelet.visual_report,
                rppg_result=output.r_ppg.result,
                rppg_conf=output.r_ppg.confidence_score,
                rppg_image=output.r_ppg.visual_report,
                stt_risk_level=output.stt.risk_level,
                stt_script=STTScript(
                    keywords=output.stt.keywords,
                    risk_reason=output.stt.risk_reason,
                    transcript=output.stt.transcript,
                    search_results=output.stt.search_results,
                ),
            ),
        )
        CRUDVideo.update_status(db, src.video_id, VideoStatus.COMPLETED)
        publish_notification(
            WorkerPubSubAPI(
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

        if output.unite is None:
            assert output.status == Status.ERROR
            CRUDVideo.update_status(db, src.video_id, VideoStatus.FAILED)
            return None

        result = CRUDResult.create(
            db,
            Result(
                user_id=src.video.user_id,
                video_id=src.video.video_id,
                total_result=output.result,
                is_fast=False,
            ),
        )
        CRUDDeepReport.create(
            db,
            DeepReport(
                user_id=src.video.user_id,
                result_id=result.result_id,
                unite_result=output.unite.result,
                unite_conf=output.unite.confidence_score,
            ),
        )
        CRUDVideo.update_status(db, src.video_id, VideoStatus.COMPLETED)
        publish_notification(
            WorkerPubSubAPI(
                user_id=src.video.user_id,
                result_id=result.result_id,
            )
        )
        return result.result_id
