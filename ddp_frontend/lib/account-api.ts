const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer' | string;
  user_id: number;
  email: string;
  nickname: string;
};

async function readErrorText(res: Response) {
  try {
    const text = await res.text();
    return text || res.statusText;
  } catch {
    return res.statusText;
  }
}

/**
 * ✅ 로그인
 * POST /auth/login
 * body: { email, password }
 */
export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`로그인 실패 (${res.status}): ${msg}`);
  }

  return res.json();
}

/**
 * ✅ 로그아웃
 * POST /auth/logout
 * header: Authorization: Bearer <refresh_token>
 */
export async function logout(refreshToken: string): Promise<{ status?: string; message?: string }> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${refreshToken}`,
    },
  });

  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`로그아웃 실패 (${res.status}): ${msg}`);
  }

  // 백엔드가 json을 안 줄 수도 있어서 방어
  try {
    return await res.json();
  } catch {
    return { status: 'success' };
  }
}

/**
 * ✅ 토큰 재발급
 * POST /auth/reissue
 * header: Authorization: Bearer <refresh_token>
 */
export async function reissue(refreshToken: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/reissue`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${refreshToken}`,
    },
  });

  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`토큰 갱신 실패 (${res.status}): ${msg}`);
  }

  return res.json();
}

/**
 * ✅ 회원 탈퇴
 * DELETE /user/withdraw
 * header: Authorization: Bearer <access_token>
 */
export async function withdraw(accessToken: string): Promise<{ status?: string; message?: string }> {
  const res = await fetch(`${API_BASE}/user/withdraw`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`탈퇴 실패 (${res.status}): ${msg}`);
  }

  try {
    return await res.json();
  } catch {
    return { status: 'success' };
  }
}