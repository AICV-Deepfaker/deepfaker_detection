from __future__ import annotations

import asyncio
import shutil
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import cv2
import torch
from pydantic import BaseModel

from ddp_backend.schemas import BaseReport, VideoReport


class HasPath(BaseModel):
    model_path: str | Path


class HasThreshold(BaseModel):
    threshold: float = 0.5


class HasNormalize(BaseModel):
    mean: tuple[float, float, float]
    std: tuple[float, float, float]


class VideoInferenceResult(BaseModel):
    prob: float
    base64_report: str


class BaseVideoConfig(HasPath, HasThreshold):
    img_size: int


class BaseDetector[Config: BaseModel, Report: BaseReport](ABC):
    model_name: str

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def load_model(self):
        pass

    @abstractmethod
    async def _analyze(self, vid_path: str | Path) -> BaseModel:
        pass

    @abstractmethod
    async def analyze(self, vid_path: str | Path) -> Report:
        pass


class BaseVideoDetector[C: BaseVideoConfig](BaseDetector[C, VideoReport]):
    def __init__(self, config: C):
        super().__init__(config)
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

    async def set_fps(
        self, vid_src: str | Path, vid_dest: str | Path, target_fps: int = 30
    ):
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

        # 3. 비동기 서브프로세스 실행
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # 실행 완료 대기 및 로그 캡처
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(
                f"FFMPEG failed with return code {process.returncode}: {error_msg}"
            )

    @abstractmethod
    async def _analyze(self, vid_path: str | Path) -> VideoInferenceResult:
        pass

    async def analyze(self, vid_path: str | Path) -> VideoReport:
        vid_path = Path(vid_path)
        await self.set_fps(vid_path, vid_path.with_stem(f"resize_{vid_path.stem}"))
        analyze_res = await self._analyze(vid_path)

        res = "FAKE" if analyze_res.prob > 0.5 else "REAL"
        confidence = (
            analyze_res.prob if analyze_res.prob > 0.5 else 1 - analyze_res.prob
        )

        return VideoReport(
            status="success",
            model_name=self.model_name,
            result=res,
            probability=round(analyze_res.prob, 4),
            confidence_score=f"{round(confidence * 100, 2)}",
            visual_report=analyze_res.base64_report,
        )
