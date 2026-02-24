import { router } from 'expo-router';

import { reissue } from './account-api';
import { clearAuth, getAuth, setAuth } from './auth-storage';

/**
 * 인증이 필요한 API 함수를 호출합니다.
 *
 * 흐름:
 * 1. 저장소에서 access_token 꺼냄
 *    - 없으면 → 로그인 화면으로 이동
 * 2. access_token으로 API 호출
 *    - 200 OK → 결과 반환
 *    - 401 → refresh_token으로 재발급 시도
 * 3. 재발급 성공 → 새 토큰 저장 후 원래 요청 재시도
 *    재발급 실패 → 저장소 초기화 후 로그인 화면으로 이동
 */
export async function withAuth<T>(fn: (accessToken: string) => Promise<T>): Promise<T> {
  const auth = await getAuth();

  // Step 1: access_token 없으면 로그인으로 이동
  if (!auth?.accessToken) {
    router.replace('/login');
    throw new Error('로그인이 필요합니다');
  }

  try {
    // Step 2: access_token으로 API 호출
    return await fn(auth.accessToken);
  } catch (err: any) {
    const is401 = err?.message?.includes('(401)');
    if (!is401 || !auth.refreshToken) throw err;

    // Step 3: access_token 만료 → refresh_token으로 재발급
    try {
      const newTokens = await reissue(auth.refreshToken);
      await setAuth({
        ...auth,
        accessToken: newTokens.access_token,
        refreshToken: newTokens.refresh_token,
      });
      // 재발급 성공 → 원래 요청 재시도
      return await fn(newTokens.access_token);
    } catch {
      // refresh_token도 만료 → 로그아웃 처리
      await clearAuth();
      router.replace('/login');
      throw new Error('세션이 만료되었습니다. 다시 로그인해 주세요.');
    }
  }
}
