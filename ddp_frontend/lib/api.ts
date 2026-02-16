const API_BASE = 'https://cheri-unarbored-gaylord.ngrok-free.dev';

export type PredictMode = 'fast' | 'deep';

/** 증거수집모드(fast)용 세부 결과 - 백엔드 확장 시 사용 */
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

export interface PredictResult {
  status: 'success' | 'error';
  result?: 'FAKE' | 'REAL';
  average_fake_prob?: number;
  confidence_score?: string;
  visual_report?: string; // Base64 이미지 데이터
  analysis_mode?: string;
  message?: string;
  // 증거수집모드 확장 필드 (백엔드 지원 시)
  frequency?: EvidenceSection;
  rppg?: EvidenceSection;
  stt_keywords?: { keyword: string; detected: boolean }[];
  // 정밀탐지모드 확장 필드
  unite?: UniteSection;
}

/**
 * 영상 파일로 딥페이크 추론 요청
 */
export async function predictWithFile(
  videoUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const formData = new FormData();
  formData.append('file', {
    uri: videoUri,
    name: 'video.mp4',
    type: 'video/mp4',
  } as unknown as Blob);
  formData.append('mode', mode);

  const response = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    body: formData,
    headers: {
      'ngrok-skip-browser-warning': 'true', // ngrok 무료판 방지 페이지 스킵
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`서버 오류 (${response.status}): ${text || response.statusText}`);
  }

  return response.json();
}

/** URI 확장자로 MIME 타입·파일명 결정 (GIF, PNG, JPEG 등) */
function getImageMimeAndName(uri: string): { type: string; name: string } {
  const lower = uri.toLowerCase();
  if (lower.includes('.gif')) return { type: 'image/gif', name: 'image.gif' };
  if (lower.includes('.png')) return { type: 'image/png', name: 'image.png' };
  if (lower.includes('.webp')) return { type: 'image/webp', name: 'image.webp' };
  return { type: 'image/jpeg', name: 'image.jpg' };
}

/**
 * 이미지 파일로 딥페이크 추론 요청 (영상과 동일한 /predict 엔드포인트)
 * GIF, PNG, JPEG 등 확장자에 맞춰 MIME 타입 전송
 */
export async function predictWithImageFile(
  imageUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const { type, name } = getImageMimeAndName(imageUri);
  const formData = new FormData();
  formData.append('file', {
    uri: imageUri,
    name,
    type,
  } as unknown as Blob);
  formData.append('mode', mode);

  const response = await fetch(`${API_BASE}/predict`, {
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

  return response.json();
}
