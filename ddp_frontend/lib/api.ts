import { getAuth } from './auth-storage';

const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');
// http(s) → ws(s) 변환 (WebSocket base URL)
const WS_BASE = API_BASE.replace(/^http/, 'ws');

export type PredictMode = 'fast' | 'deep';

/** 증거수집모드(fast)용 세부 결과 */
export interface EvidenceSection {
  result?: 'FAKE' | 'REAL' | 'UNKNOWN';
  probability?: number;
  visual_url?: string; // S3 presigned URL
}

/** 정밀탐지모드(deep)용 UNITE 결과 */
export interface UniteSection {
  result?: 'FAKE' | 'REAL' | 'UNKNOWN';
  probability?: number;
}

export interface SttSearchResult {
  keyword: string;
  title: string;
  url: string;
  content: string;
}

export interface PredictResult {
  status: 'success' | 'error';
  result?: 'FAKE' | 'REAL' | 'UNKNOWN';
  average_fake_prob?: number;
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
  result_id?: string;
}

/**
 * 백엔드 응답(APIOutputFast / APIOutputDeep)을 프론트 PredictResult 형태로 변환
 */
// 이거 그냥 바로 받기 (형태 변환 X) -> raw 그대로 반환
function mapBackendResponse(raw: any, mode: PredictMode): PredictResult {
  if (raw.status === 'error' || raw.error_msg) {
    return {
      status: 'error',
      message: raw.error_msg ?? '서버 오류가 발생했습니다.',
      analysis_mode: mode,
    };
  }

  if (mode === 'fast') {
    // wavelet: { probability, result(computed), visual_report(URL) }
    // r_ppg:   { visual_report(URL) }  ← probability/result 없음
    const wavelet = raw.wavelet ?? {};
    const rppg = raw.r_ppg ?? {};
    const stt = raw.stt ?? {};

    return {
      status: 'success',
      analysis_mode: 'fast',
      result: raw.result,                   // 전체 판정은 top-level result 사용
      average_fake_prob: wavelet.probability,

      frequency: {
        result: wavelet.result,
        probability: wavelet.probability,
        visual_url: wavelet.visual_report,  // URL (S3 presigned)
      },
      rppg: {
        // r_ppg는 visual만 있고 result/probability 없음
        visual_url: rppg.visual_report,
      },

      stt_risk_level: stt.risk_level,
      stt_risk_reason: stt.risk_reason,
      stt_transcript: stt.transcript,
      stt_search_results: stt.search_results ?? [],
      stt_keywords: (stt.keywords ?? []).map((k: string) => ({ keyword: k, detected: true })),
    };
  }

  // deep mode: unite: { probability, result(computed) }
  const unite = raw.unite ?? {};
  return {
    status: 'success',
    analysis_mode: 'deep',
    result: raw.result,
    average_fake_prob: unite.probability,
    unite: {
      result: unite.result,
      probability: unite.probability,
    },
  };
}

/** Authorization 헤더용 access token 가져오기 */
async function getAuthHeader(): Promise<Record<string, string>> {
  const auth = await getAuth();
  if (auth?.accessToken) {
    return { Authorization: `Bearer ${auth.accessToken}` };
  }
  return {};
}

/** ms 대기 */
function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

/**
 * WebSocket으로 result_id 수신 대기.
 * 서버가 분석 완료 시 result_id (UUID string)를 text로 push한다.
 */
function waitForResultViaWS(token: string, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(new Error('취소됨'));

    const ws = new WebSocket(`${WS_BASE}/ws?token=${token}`);
    let settled = false;

    const finish = (fn: () => void) => {
      if (!settled) {
        settled = true;
        ws.close();
        fn();
      }
    };

    ws.onmessage = (e: MessageEvent) => finish(() => resolve(String(e.data)));
    ws.onerror = () => finish(() => reject(new Error('WebSocket 연결 오류')));
    ws.onclose = (e: CloseEvent) => {
      if (!settled && e.code !== 1000) {
        finish(() => reject(new Error(`WebSocket 연결 종료 (code: ${e.code})`)));
      }
    };

    signal.addEventListener('abort', () =>
      finish(() => reject(new Error('취소됨')))
    );
  });
}

/**
 * HTTP 폴링으로 result_id 수신 대기.
 * GET /prediction/status/{video_id} → { status, result_id? }
 * 최대 180초 (3초 간격 × 60회) 대기
 */
async function pollForResultId(
  videoId: string,
  authHeaders: Record<string, string>,
  signal: AbortSignal
): Promise<string> {
  const MAX_TRIES = 60;
  for (let i = 0; i < MAX_TRIES; i++) {
    if (signal.aborted) throw new Error('취소됨');
    await delay(3000);
    if (signal.aborted) throw new Error('취소됨');

    const statusRes = await fetch(`${API_BASE}/prediction/status/${videoId}`, {
      headers: { 'ngrok-skip-browser-warning': 'true', ...authHeaders },
    });
    if (!statusRes.ok) continue;

    const statusData = await statusRes.json();
    if (statusData.result_id) return statusData.result_id as string;
    if (statusData.status === 'failed') throw new Error('분석 처리 중 오류가 발생했습니다.');
  }
  throw new Error('분석 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.');
}

/**
 * WebSocket + 폴링을 동시에 시작하고 먼저 result_id를 받은 쪽으로 처리.
 */
async function waitForResultId(
  videoId: string,
  token: string,
  authHeaders: Record<string, string>
): Promise<string> {
  const abortCtrl = new AbortController();
  try {
    return await Promise.race([
      waitForResultViaWS(token, abortCtrl.signal),
      pollForResultId(videoId, authHeaders, abortCtrl.signal),
    ]);
  } finally {
    abortCtrl.abort(); // 승자가 결정된 후 나머지 정리
  }
}

/**
 * result_id로 실제 분석 결과를 가져온 뒤 PredictResult로 변환.
 */
async function fetchResult(
  resultId: string,
  mode: PredictMode,
  authHeaders: Record<string, string>
): Promise<PredictResult> {
  const resultRes = await fetch(`${API_BASE}/prediction/result/${resultId}`, {
    headers: { 'ngrok-skip-browser-warning': 'true', ...authHeaders },
  });
  if (!resultRes.ok) {
    const text = await resultRes.text();
    throw new Error(`결과 조회 실패 (${resultRes.status}): ${text}`);
  }
  const raw = await resultRes.json();
  // 시각화 URL 디버그 로그 (이미지가 안 보이면 여기서 URL 확인)
  console.log('[API] wavelet.visual_report:', raw.wavelet?.visual_report);
  console.log('[API] r_ppg.visual_report:', raw.r_ppg?.visual_report);
  const mapped = mapBackendResponse(raw, mode);
  return { ...mapped, result_id: resultId };
}

/**
 * 영상 파일로 딥페이크 추론 요청
 * 1) POST /prediction/{mode} → video_id 수신 (202 Accepted)
 * 2) WebSocket + 폴링 race로 result_id 대기
 * 3) GET /prediction/result/{result_id} → 최종 결과
 */
export async function predictWithFile(
  videoUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const endpoint = mode === 'fast' ? '/prediction/fast' : '/prediction/deep';
  const authHeaders = await getAuthHeader();
  const token = authHeaders['Authorization']?.replace('Bearer ', '') ?? '';

  const formData = new FormData();
  formData.append('file', {
    uri: videoUri,
    name: 'video.mp4',
    type: 'video/mp4',
  } as unknown as Blob);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData,
    headers: { 'ngrok-skip-browser-warning': 'true', ...authHeaders },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`서버 오류 (${response.status}): ${text || response.statusText}`);
  }

  const { video_id: videoId }: { video_id: string } = await response.json();
  const resultId = await waitForResultId(videoId, token, authHeaders);
  return fetchResult(resultId, mode, authHeaders);
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
 * ✅ 영상 파일을 S3에 업로드
 * POST /videos/upload  (multipart/form-data)
 */
export type VideoUploadResponse = {
  video_id: string;
  s3_path: string;
  queued: boolean;
};

export async function uploadVideo(
  accessToken: string,
  videoUri: string
): Promise<VideoUploadResponse> {
  const filename = videoUri.split('/').pop() ?? 'video.mp4';
  const match = /\.(\w+)$/.exec(filename);
  const type = match ? `video/${match[1].toLowerCase()}` : 'video/mp4';

  const formData = new FormData();
  formData.append('file', { uri: videoUri, name: filename, type } as unknown as Blob);

  const res = await fetch(`${API_BASE}/videos/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`영상 업로드 실패 (${res.status}): ${text}`);
  }
  return res.json();
}

/**
 * ✅ YouTube 링크를 S3에 업로드 (백그라운드 처리)
 * POST /videos/link
 */
export type VideoLinkResponse = {
  video_id: string;
  queued: boolean;
};

export async function linkVideo(
  accessToken: string,
  url: string
): Promise<VideoLinkResponse> {
  const res = await fetch(`${API_BASE}/videos/link`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`링크 업로드 실패 (${res.status}): ${text}`);
  }
  return res.json();
}

/** JWT payload에서 user_id(UUID) 추출 */
function getUserIdFromToken(token: string): string | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) base64 += '=';
    const payload = JSON.parse(atob(base64));
    return payload.user_id ?? null;
  } catch {
    return null;
  }
}

/**
 * WebSocket으로 result_id 수신 대기 (새 버전: /ws/{user_id} 경로 사용)
 */
function waitForResultViaWSV2(userId: string, token: string, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(new Error('취소됨'));

    // React Native WebSocket은 세 번째 인자로 headers를 지원한다
    const ws = new (WebSocket as any)(
      `${WS_BASE}/ws/${userId}`,
      undefined,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    let settled = false;

    const finish = (fn: () => void) => {
      if (!settled) {
        settled = true;
        ws.close();
        fn();
      }
    };

    ws.onmessage = (e: MessageEvent) => finish(() => resolve(String(e.data)));
    ws.onerror = () => finish(() => reject(new Error('WebSocket 연결 오류')));
    ws.onclose = (e: CloseEvent) => {
      if (!settled && e.code !== 1000) {
        finish(() => reject(new Error(`WebSocket 연결 종료 (code: ${e.code})`)));
      }
    };

    signal.addEventListener('abort', () =>
      finish(() => reject(new Error('취소됨')))
    );
  });
}

/**
 * 분석 요청 트리거
 * POST /prediction/{mode}?video_id={videoId}
 */
export async function triggerAnalysis(
  accessToken: string,
  videoId: string,
  mode: PredictMode,
): Promise<void> {
  const res = await fetch(`${API_BASE}/prediction/${mode}?video_id=${videoId}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'ngrok-skip-browser-warning': 'true',
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`분석 요청 실패 (${res.status}): ${text}`);
  }
}

/**
 * video_id 기반 딥페이크 추론 전체 흐름
 * 1) Source 준비 대기 (링크 영상의 경우 YouTube 다운로드 완료까지)
 * 2) POST /prediction/{mode}?video_id={videoId}
 * 3) WebSocket /ws/{user_id} 로 result_id 대기
 * 4) GET /prediction/result/{result_id} → 최종 결과
 */
export async function predictWithVideoId(
  videoId: string,
  mode: PredictMode = 'deep',
): Promise<PredictResult> {
  const authHeaders = await getAuthHeader();
  const token = authHeaders['Authorization']?.replace('Bearer ', '') ?? '';
  const userId = getUserIdFromToken(token);
  if (!userId) throw new Error('인증 정보를 찾을 수 없습니다. 다시 로그인해주세요.');

  // 1. Source 준비 대기: 409면 아직 업로드 중이므로 재시도
  const MAX_WAIT = 60; // 최대 60초 대기
  for (let i = 0; i < MAX_WAIT; i++) {
    const res = await fetch(`${API_BASE}/prediction/${mode}?video_id=${videoId}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': 'true' },
    });
    if (res.ok) break;
    if (res.status === 409) {
      await delay(1000);
      continue;
    }
    const text = await res.text();
    throw new Error(`분석 요청 실패 (${res.status}): ${text}`);
  }

  // 2. WebSocket + 폴링 race로 result_id 대기
  const abortCtrl = new AbortController();
  try {
    const resultId = await Promise.race([
      waitForResultViaWSV2(userId, token, abortCtrl.signal),
      pollForResultId(videoId, authHeaders, abortCtrl.signal),
    ]);
    // 3. 결과 조회
    return fetchResult(resultId, mode, authHeaders);
  } finally {
    abortCtrl.abort();
  }
}

/**
 * 이미지 파일로 딥페이크 추론 요청 (영상과 동일한 흐름)
 */
export async function predictWithImageFile(
  imageUri: string,
  mode: PredictMode = 'deep'
): Promise<PredictResult> {
  const endpoint = mode === 'fast' ? '/prediction/fast' : '/prediction/deep';
  const { type, name } = getImageMimeAndName(imageUri);
  const authHeaders = await getAuthHeader();
  const token = authHeaders['Authorization']?.replace('Bearer ', '') ?? '';

  const formData = new FormData();
  formData.append('file', { uri: imageUri, name, type } as unknown as Blob);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData,
    headers: { 'ngrok-skip-browser-warning': 'true', ...authHeaders },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`서버 오류 (${response.status}): ${text || response.statusText}`);
  }

  const { video_id: videoId }: { video_id: string } = await response.json();
  const resultId = await waitForResultId(videoId, token, authHeaders);
  return fetchResult(resultId, mode, authHeaders);
}

/**
 * 포인트 조회
 */
export type UserMeResponse = {
  active_points: number;
  total_points?: number;
  profile_image?: string;
};

export async function getMe(): Promise<UserMeResponse> {
  const authHeaders = await getAuthHeader();
  const res = await fetch(`${API_BASE}/me`, {
    method: 'GET',
    headers: { 'ngrok-skip-browser-warning': 'true', ...authHeaders },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`내 정보 조회 실패 (${res.status}): ${text}`);
  }
  return res.json();
}

export async function postAlert(body: { result_id: string | number }): Promise<any> {
  const authHeaders = await getAuthHeader();
  const res = await fetch(`${API_BASE}/alerts`, {
    method: 'POST',
    headers: {
      'ngrok-skip-browser-warning': 'true',
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`신고 실패 (${res.status}): ${text}`);
  }
  return res.json().catch(() => ({}));
}