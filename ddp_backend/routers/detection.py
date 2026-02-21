from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from ddp_backend.schemas import (
    APIOutputDeep,
    APIOutputFast,
)
from ddp_backend.services.dependencies import detection_pipeline
from ddp_backend.utils.file_handler import save_temp_file


router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.post(path="/fast")
def predict_deepfake_fast(
    file: Annotated[UploadFile, File(...)],
) -> APIOutputFast:
    with save_temp_file(file) as temp_path:
        return detection_pipeline.run_fast_mode(temp_path)


@router.post("/deep")
def predict_deepfake_deep(
    file: Annotated[UploadFile, File(...)],
) -> APIOutputDeep:
    with save_temp_file(file) as temp_path:
        return detection_pipeline.run_deep_mode(temp_path)
