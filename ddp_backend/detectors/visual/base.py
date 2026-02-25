from __future__ import annotations

import shutil
import subprocess
from abc import abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import cv2
import torch
from pydantic import BaseModel

from ddp_backend.core.s3 import upload_file_to_s3
from ddp_backend.schemas.config import BaseVideoConfig
from ddp_backend.schemas.enums import Result, Status
from ddp_backend.schemas.report import VideoReport
from ddp_backend.detectors import VisualDetector


class VideoInferenceResult(BaseModel):
    prob: float
    image: bytes | None = None


class BaseVideoDetector[C: BaseVideoConfig](VisualDetector):
    """
    BaseVideoDetector[C: BaseVideoConfig] for Config.
    """

    def __init__(self, config: C):
        self.config = config
        self.device: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    @contextmanager
    def _load_video(
        self, vid_path: str | Path
    ) -> Generator[cv2.VideoCapture, None, None]:
        cap = None
        try:
            cap = cv2.VideoCapture(vid_path)
            if not cap.isOpened():
                raise FileNotFoundError(f"File {vid_path} not found.")
            yield cap
        finally:
            if cap is not None:
                cap.release()

    def set_fps(self, vid_src: str | Path, vid_dest: str | Path, target_fps: int = 30):
        # 1. 현재 FPS 확인 (OpenCV 활용)
        with self._load_video(vid_src) as cap:
            current_fps = cap.get(cv2.CAP_PROP_FPS)

        # 현재 FPS와 타겟 FPS가 같다면 처리를 스킵하거나 단순히 복사할 수 있습니다.
        if int(current_fps) == target_fps:
            shutil.copy(vid_src, vid_dest)
            # shutil.copy(vid_src, vid_dest) 등 추가 가능
            return

        # 2. FFMPEG 명령어 구성
        # -y: 출력 파일 덮어쓰기 허용
        # -i: 입력 파일
        # -filter:v fps=fps=30: 비디오 필터를 사용하여 FPS 조정 (프레임 드랍/복제 방식)
        # -c:a copy: 오디오는 재인코딩 없이 그대로 복사 (속도 향상 및 품질 유지)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(vid_src),
            "-filter:v",
            f"fps=fps={target_fps}",
            "-c:a",
            "copy",
            str(vid_dest),
        ]

        # 3. 동기 서브프로세스 실행
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # 이 설정을 통해 stderr를 바이트가 아닌 문자열로 바로 받습니다.
        )

        # 실행 완료 후 리턴코드 확인
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            raise RuntimeError(
                f"FFMPEG failed with returncode {result.returncode}: {error_msg}"
            )

    @abstractmethod
    def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        pass

    def analyze(self, vid_path: str | Path) -> VideoReport:
        vid_path = Path(vid_path)
        resized_path = vid_path.with_stem(f"resize_{vid_path.stem}")
        self.set_fps(vid_path, resized_path)

        try:
            analyze_res = self._analyze(resized_path)
        except RuntimeError:
            return VideoReport(
                status=Status.ERROR,
                model_name=self.model_name,
                result=Result.UNKNOWN,
                probability=0,
                visual_report=None,
            )

        res = Result.FAKE if analyze_res.prob > 0.5 else Result.REAL
        s3_key: str | None = None
        if analyze_res.image is not None:
            upload_key = f"report/{vid_path.stem}_{self.model_name}_analyzed.png"

            s3_key = upload_file_to_s3(
                BytesIO(analyze_res.image), upload_key, "image/png"
            )

        return VideoReport(
            status=Status.SUCCESS,
            model_name=self.model_name,
            result=res,
            probability=analyze_res.prob,
            visual_report=s3_key,
        )
