from typing import Literal, Annotated
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # macOS Conda OpenMP 충돌 방지

import subprocess
import tempfile
from pathlib import Path
from dataclasses import field

import instructor
from pydantic import BaseModel, Field
from faster_whisper import WhisperModel
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# 사기 관련 탐지 키워드 seed
SCAM_SEED_KEYWORDS:list[str] = [
    "투자", "도박", "코인", "대출", "송금", "수익", "이자", "원금 보장",
    "비트코인", "이더리움", "선물", "레버리지", "리딩방", "고수익",
    "불법", "사기", "피싱", "보이스피싱", "로또", "환전", "계좌이체",
]

type RiskLevel = Literal['high', 'medium', 'low', 'none']
class STTPipelineResult(BaseModel):
    video_path: str
    transcript: str
    detected_keywords: list[str]
    risk_level: RiskLevel
    risk_reason: str
    search_results: list[dict[str, str]] = field(default_factory=list[dict[str, str]])


def extract_audio(video_path: str | Path) -> str:
    """ffmpeg으로 비디오에서 오디오(WAV) 추출. 임시파일 경로 반환."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vn",                    # 비디오 스트림 제외
            "-acodec", "pcm_s16le",   # 16-bit PCM
            "-ar", "16000",           # 16kHz (Whisper 권장)
            "-ac", "1",               # 모노
            tmp.name, "-y",           # 출력, 덮어쓰기
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return tmp.name


def transcribe(audio_path: str | Path, model_size: str = "base") -> str:
    """Faster-Whisper로 음성 → 텍스트 변환 (한국어 우선 감지)."""
    print(f"  [STT] Whisper 모델 로드 중 ({model_size})...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), language="ko", beam_size=5)
    text = " ".join(seg.text.strip() for seg in segments)
    print(f"  [STT] 언어: {info.language}, 확률: {info.language_probability:.2f}")
    return text

class Keywords(BaseModel):
    detected_keywords: Annotated[list[str], Field(description="List of detected keywords")]
    risk_level: RiskLevel
    reason: Annotated[str, Field(description="위험 판단 근거 한 줄 설명")]


def extract_keywords_with_groq(transcript: str, client: Groq, model: str = "llama-3.3-70b-versatile") -> Keywords:
    """Groq LLM으로 텍스트에서 사기 관련 키워드 및 위험도 추출."""
    seed_str = ", ".join(SCAM_SEED_KEYWORDS)

    prompt = (
        "다음 텍스트를 분석하여 투자/도박/코인/대출/송금 등 금융 사기와 관련된 "
        "키워드를 추출하고 위험도를 평가해주세요.\n\n"
        f"참고 키워드 목록: {seed_str}\n\n"
        f"분석할 텍스트:\n{transcript}\n\n"
    )
    instruct_client = instructor.from_provider(f'groq/{model}', async_client=False, api_key=client.api_key)

    completion = instruct_client.create(
        messages=[{"role": "user", "content": prompt}],
        response_model=Keywords
    )
    return completion


def search_latest_cases(keywords: list[str], tavily_client: TavilyClient) -> list[dict[str, str]]:
    """Tavily로 키워드별 최신 사기 사례 검색."""
    results = []
    for kw in keywords[:3]:  # 상위 3개 키워드만 검색
        query = f"딥페이크 {kw} 금융사기 최신 사례"
        print(f"  [Search] 검색 중: {query}")
        response = tavily_client.search(query=query, max_results=3)
        for item in response.get("results", []):
            results.append(
                {
                    "keyword": kw,
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:500],  # 앞 300자만
                }
            )
    return results


def run_pipeline(video_path: str, whisper_model: str = "base") -> STTPipelineResult:
    """전체 파이프라인 실행: 비디오 → STT → 키워드 추출 → 검색."""
    groq_key = os.getenv("GROQ_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not groq_key:
        raise ValueError("GROQ_API_KEY 환경변수가 설정되지 않았습니다.")
    if not tavily_key:
        raise ValueError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")

    groq_client = Groq(api_key=groq_key)
    tavily =TavilyClient(api_key=tavily_key)

    print(f"\n[1/4] 오디오 추출: {video_path}")
    audio_path = extract_audio(video_path)

    try:
        print("[2/4] 음성 → 텍스트 변환 (Faster-Whisper)")
        transcript = transcribe(audio_path, model_size=whisper_model)
        print(f"  전사 결과 ({len(transcript)}자): {transcript[:200]}...")

        print("[3/4] Groq로 키워드 및 위험도 분석")
        kw_result = extract_keywords_with_groq(transcript, groq_client)
        print(f"  감지 키워드: {kw_result.detected_keywords}")
        print(f"  위험도: {kw_result.risk_level} — {kw_result.reason}")

        search_results = []
        if kw_result.detected_keywords and kw_result.risk_level != "none":
            print("[4/4] Tavily로 최신 사례 검색")
            search_results = search_latest_cases(kw_result.detected_keywords, tavily)
        else:
            print("[4/4] 사기 관련 키워드 없음 → 검색 생략")

    finally:
        os.unlink(audio_path)  # 임시 오디오 파일 삭제

    return STTPipelineResult(
        video_path=video_path,
        transcript=transcript,
        detected_keywords=kw_result.detected_keywords,
        risk_level=kw_result.risk_level,
        risk_reason=kw_result.reason,
        search_results=search_results,
    )
