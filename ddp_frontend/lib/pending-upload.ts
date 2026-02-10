/**
 * 홈에서 선택한 이미지/영상 URI를 URL 파라미터 없이 챗봇으로 전달.
 * (긴 file:// URI가 쿼리에서 잘리거나 깨지는 것 방지)
 */
let pendingImageUri: string | null = null;
let pendingVideoUri: string | null = null;

export function setPendingImageUri(uri: string) {
  pendingImageUri = uri;
}

export function takePendingImageUri(): string | null {
  const u = pendingImageUri;
  pendingImageUri = null;
  return u;
}

export function setPendingVideoUri(uri: string) {
  pendingVideoUri = uri;
}

export function takePendingVideoUri(): string | null {
  const u = pendingVideoUri;
  pendingVideoUri = null;
  return u;
}
