from pathlib import Path

from ddp_backend.detectors.audio import STTDetector
from ddp_backend.detectors.visual import RPPGDetector, UniteDetector, WaveletDetector
from ddp_backend.schemas.api import APIOutputDeep, APIOutputFast
from ddp_backend.schemas.enums import AnalyzeMode, Status, Result


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
        self.wavelet_detector.load_model()
        self.r_ppg_detector.load_model()

    def run_fast_mode(self, file_path: Path) -> APIOutputFast:
        try:
            wavelet_report = self.wavelet_detector.analyze(file_path)
            r_ppg_report = self.r_ppg_detector.analyze(file_path)
            stt_report = self.stt_detector.analyze(file_path)

            result:Result
            if wavelet_report.result > r_ppg_report.result:
                result = wavelet_report.result
            elif wavelet_report.result < r_ppg_report.result:
                result = r_ppg_report.result
            else:
                result = Result.UNKNOWN

            return APIOutputFast(
                status=Status.SUCCESS,
                analysis_mode=AnalyzeMode.FAST,
                result=result,
                wavelet=wavelet_report,
                r_ppg=r_ppg_report,
                stt=stt_report,
            )
        except Exception as e:
            return APIOutputFast(
                status=Status.ERROR,
                error_msg=str(e),
                result=Result.UNKNOWN,
                analysis_mode=AnalyzeMode.FAST,
            )

    def run_deep_mode(self, file_path: Path) -> APIOutputDeep:
        try:
            unite_report = self.unite_detector.analyze(file_path)
            return APIOutputDeep(
                status=Status.SUCCESS,
                analysis_mode=AnalyzeMode.DEEP,
                result=unite_report.result,
                unite=unite_report,
            )
        except Exception as e:
            return APIOutputDeep(
                status=Status.ERROR,
                error_msg=str(e),
                result=Result.UNKNOWN,
                analysis_mode=AnalyzeMode.DEEP,
            )