from pathlib import Path

from ddp_backend.detectors.audio import STTDetector
from ddp_backend.detectors.visual import RPPGDetector, UniteDetector, WaveletDetector
from ddp_backend.schemas.report import DeepReportData, FastReportData, STTScript


class DetectionPipeline:
    def __init__(
        self,
        unite: UniteDetector,
        wavelet: WaveletDetector,
        r_ppg: RPPGDetector,
        stt: STTDetector,
    ):
        self.unite_detector = unite
        self.wavelet_detector = wavelet
        self.r_ppg_detector = r_ppg

        self.stt_detector = stt

    def load_all_models(self):
        self.unite_detector.load_model()
        try:
            self.wavelet_detector.load_model()
        except Exception as e:
            print(f"[WARN] Wavelet model load failed: {e}")
        self.r_ppg_detector.load_model()

    def run_fast_mode(self, file_path: Path) -> FastReportData:
        print(f"[PIPELINE] Starting wavelet analysis: {file_path}")
        wavelet_report = self.wavelet_detector.analyze(file_path)
        print(f"[PIPELINE] Wavelet done. Starting rPPG analysis.")
        r_ppg_report = self.r_ppg_detector.analyze(file_path)
        print(f"[PIPELINE] rPPG done. Starting STT analysis.")
        stt_report = self.stt_detector.analyze(file_path)
        print(f"[PIPELINE] STT done.")

        if wavelet_report.content is None or r_ppg_report.content is None:
            raise RuntimeError("Content is empty.")

        return FastReportData(
            freq_result=wavelet_report.content.result,
            freq_conf=wavelet_report.content.confidence_score,
            freq_image=wavelet_report.content.visual_report,
            rppg_image=r_ppg_report.content.visual_report,
            stt_risk_level=stt_report.risk_level,
            stt_script=STTScript(
                keywords=stt_report.keywords,
                risk_reason=stt_report.risk_reason,
                transcript=stt_report.transcript,
                search_results=stt_report.search_results,
            ),
        )

    def run_deep_mode(self, file_path: Path) -> DeepReportData:
        unite_report = self.unite_detector.analyze(file_path)
        if unite_report.content is None:
            raise RuntimeError("Content is empty")
        return DeepReportData(
            unite_result=unite_report.content.result,
            unite_conf=unite_report.content.confidence_score
        )