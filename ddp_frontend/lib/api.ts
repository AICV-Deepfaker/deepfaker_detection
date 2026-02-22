const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');

export type PredictMode = 'fast' | 'deep';

/** 증거수집모드(fast)용 세부 결과 */
export interface EvidenceSection {
  result?: 'FAKE' | 'REAL';
  probability?: number;
  confidence_score?: string;
  accuracy?: string;
  visual_base64?: string;
}

/** 정밀탐지모드(deep)용 UNITE 결과 */
export interface UniteSection {
  result?: 'FAKE' | 'REAL';
  probability?: number;
  confidence_score?: string;
  accuracy?: string;
}

export interface SttSearchResult {
  keyword: string;
  title: string;
  url: string;
  content: string;
}

export interface PredictResult {
  status: 'success' | 'error';
  result?: 'FAKE' | 'REAL';
  average_fake_prob?: number;
  confidence_score?: string;
  visual_report?: string; // Base64 이미지 데이터
  analysis_mode?: string;
  message?: string;
  // 증거수집모드 확장 필드
  frequency?: EvidenceSection;
  rppg?: EvidenceSection;
  stt_keywords?: { keyword: string; detected: boolean }[];
  // STT 파이프라인 결과
  stt_risk_level?: 'high' | 'medium' | 'low' | 'none';
  stt_risk_reason?: string;
  stt_transcript?: string;
  stt_search_results?: SttSearchResult[];
  // 정밀탐지모드 확장 필드
  unite?: UniteSection;
}

/**
 * 백엔드 응답(APIOutputFast / APIOutputDeep)을 프론트 PredictResult 형태로 변환
 */
function mapBackendResponse(raw: any, mode: PredictMode): PredictResult {
  if (raw.status === 'error' || raw.error_msg) {
    return {
      status: 'error',
      message: raw.error_msg ?? '서버 오류가 발생했습니다.',
      analysis_mode: mode,
    };
  }

  if (mode === 'fast') {
    const wavelet = raw.wavelet ?? {};
    const rppg = raw.r_ppg ?? {};
    const stt = raw.stt ?? {};

    // FAKE 판정: wavelet 또는 r_ppg 중 하나라도 FAKE면 FAKE
    const isFake = wavelet.result === 'FAKE' || rppg.result === 'FAKE';

    return {
      status: 'success',
      analysis_mode: 'fast',
      result: isFake ? 'FAKE' : 'REAL',
      average_fake_prob: wavelet.probability ?? rppg.probability,
      confidence_score: String(wavelet.confidence_score ?? rppg.confidence_score ?? ''),
      visual_report: wavelet.visual_report ?? rppg.visual_report,

      frequency: {
        result: wavelet.result,
        probability: wavelet.probability,
        confidence_score: String(wavelet.confidence_score ?? ''),
        visual_base64: wavelet.visual_report,
      },
      rppg: {
        result: rppg.result,
        probability: rppg.probability,
        confidence_score: String(rppg.confidence_score ?? ''),
        visual_base64: rppg.visual_report,
      },

      stt_risk_level: stt.risk_level,
      stt_risk_reason: stt.risk_reason,
      stt_transcript: stt.transcript,
      stt_search_results: stt.search_results ?? [],
      stt_keywords: (stt.keywords ?? []).map((k: string) => ({ keyword: k, detected: true })),
    };
  }

  // deep mode
  const unite = raw.unite ?? {};
  return {
    status: 'success',
    analysis_mode: 'deep',
    result: unite.result,
    average_fake_prob: unite.probability,
    confidence_score: String(unite.confidence_score ?? ''),
    visual_report: unite.visual_report,
    unite: {
      result: unite.result,
      probability: unite.probability,
      confidence_score: String(unite.confidence_score ?? ''),
    },
  };
}

/**
 * 영상 파일로 딥페이크 추론 요청
 * fast → POST /prediction/fast
 * deep → POST /prediction/deep
 */
export async function predictWithFile(
  videoUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const endpoint = mode === 'fast' ? '/prediction/fast' : '/prediction/deep';

  const formData = new FormData();
  formData.append('file', {
    uri: videoUri,
    name: 'video.mp4',
    type: 'video/mp4',
  } as unknown as Blob);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData,
    headers: {
      'ngrok-skip-browser-warning': 'true',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`서버 오류 (${response.status}): ${text || response.statusText}`);
  }

  const raw = await response.json();
  return mapBackendResponse(raw, mode);
}

/** URI 확장자로 MIME 타입·파일명 결정 */
function getImageMimeAndName(uri: string): { type: string; name: string } {
  const lower = uri.toLowerCase();
  if (lower.includes('.gif')) return { type: 'image/gif', name: 'image.gif' };
  if (lower.includes('.png')) return { type: 'image/png', name: 'image.png' };
  if (lower.includes('.webp')) return { type: 'image/webp', name: 'image.webp' };
  return { type: 'image/jpeg', name: 'image.jpg' };
}

/**
 * 이미지 파일로 딥페이크 추론 요청
 * fast → POST /prediction/fast
 * deep → POST /prediction/deep
 */
export async function predictWithImageFile(
  imageUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const endpoint = mode === 'fast' ? '/prediction/fast' : '/prediction/deep';
  const { type, name } = getImageMimeAndName(imageUri);

  const formData = new FormData();
  formData.append('file', {
    uri: imageUri,
    name,
    type,
  } as unknown as Blob);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData,
    headers: {
      'ngrok-skip-browser-warning': 'true',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`서버 오류 (${response.status}): ${text || response.statusText}`);
  }

  const raw = await response.json();
  return mapBackendResponse(raw, mode);
}
