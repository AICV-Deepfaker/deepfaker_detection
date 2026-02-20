"""
딥페이크 STT 파이프라인 CLI

사용법:
    python main.py dataset/bts.mp4
    python main.py dataset/sport_star_ad.mp4 --model small
"""
import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline


def print_result(result) -> None:
    RISK_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢", "none": "⚪"}
    emoji = RISK_EMOJI.get(result.risk_level, "❓")

    print("\n" + "=" * 60)
    print(f"  파일: {Path(result.video_path).name}")
    print("=" * 60)

    print(f"\n[전사 텍스트]\n{result.transcript}\n")

    print(f"[키워드 분석]")
    print(f"  감지 키워드: {', '.join(result.detected_keywords) or '없음'}")
    print(f"  위험도: {emoji} {result.risk_level.upper()}")
    print(f"  판단 근거: {result.risk_reason}")

    if result.search_results:
        print(f"\n[관련 최신 사례 — Tavily 검색 결과]")
        for i, item in enumerate(result.search_results, 1):
            print(f"\n  [{i}] [{item['keyword']}] {item['title']}")
            print(f"      URL: {item['url']}")
            print(f"      {item['content'][:200]}")
    else:
        print("\n[관련 검색 결과 없음]")

    print("\n" + "=" * 60)


def save_result(result, output_path: str) -> None:
    data = {
        "video": result.video_path,
        "transcript": result.transcript,
        "detected_keywords": result.detected_keywords,
        "risk_level": result.risk_level,
        "risk_reason": result.risk_reason,
        "search_results": result.search_results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장됨: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="딥페이크 STT 사기 탐지 파이프라인")
    parser.add_argument("video", help="분석할 비디오 파일 경로")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper 모델 크기 (기본: base)",
    )
    parser.add_argument("--output", default=None, help="결과를 저장할 JSON 파일 경로")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다 — {video_path}")
        return

    result = run_pipeline(str(video_path), whisper_model=args.model)
    print_result(result)

    if args.output:
        save_result(result, args.output)


if __name__ == "__main__":
    main()
