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
        self.wavelet_detector.load_model()
        self.r_ppg_detector.load_model()

    def run_fast_mode(self, file_path: Path) -> FastReportData | None:
        try:
            wavelet_report = self.wavelet_detector.analyze(file_path)
            r_ppg_report = self.r_ppg_detector.analyze(file_path)
            stt_report = self.stt_detector.analyze(file_path)

            return FastReportData(
                freq_result=wavelet_report.result,
                freq_conf=wavelet_report.confidence_score,
                freq_image=wavelet_report.visual_report,
                rppg_result=r_ppg_report.result,
                rppg_conf=r_ppg_report.confidence_score,
                rppg_image=r_ppg_report.visual_report,
                stt_risk_level=stt_report.risk_level,
                stt_script=STTScript.model_validate(stt_report),
            )
        except Exception:
            return None

    def run_deep_mode(self, file_path: Path) -> DeepReportData | None:
        try:
            unite_report = self.unite_detector.analyze(file_path)
            return DeepReportData(
                unite_result=unite_report.result,
                unite_conf=unite_report.confidence_score
            )
        except Exception:
            return None