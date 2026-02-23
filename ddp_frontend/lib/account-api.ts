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
/**
 * ✅ 회원가입
 * POST /user/register
 */
export type UserRegisterRequest = {
  email: string;
  password: string;
  name: string;
  nickname: string;
  birth?: string;       // "YYYY-MM-DD"
  affiliation?: string; // "개인" | "기관" | "회사"
  profile_image?: string | null;
};

export type UserRegisterResponse = {
  user_id: number;
  email: string;
  name: string;
  nickname: string;
  created_at: string;
};

export async function register(data: UserRegisterRequest): Promise<UserRegisterResponse> {
  const res = await fetch(`${API_BASE}/user/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`회원가입 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}

/**
 * ✅ 이메일 중복 확인
 * POST /user/check-email
 */
export async function checkEmail(email: string): Promise<{ is_duplicate: boolean }> {
  const res = await fetch(`${API_BASE}/user/check-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`이메일 확인 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}

/**
 * ✅ 닉네임 중복 확인
 * POST /user/check-nickname
 */
export async function checkNickname(nickname: string): Promise<{ is_duplicate: boolean }> {
  const res = await fetch(`${API_BASE}/user/check-nickname`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname }),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`닉네임 확인 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}

/**
 * ✅ 아이디(이메일) 찾기
 * POST /user/find-id
 * body: { name, birth: "YYYY-MM-DD" }
 */
export async function findId(name: string, birth: string): Promise<{ email: string }> {
  const res = await fetch(`${API_BASE}/user/find-id`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, birth }),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`아이디 찾기 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}

/**
 * ✅ 비밀번호 찾기 (임시 비밀번호 이메일 발송)
 * POST /user/find-password
 * body: { name, birth: "YYYY-MM-DD", email }
 */
export async function findPassword(
  name: string,
  birth: string,
  email: string
): Promise<{ status?: string; message?: string }> {
  const res = await fetch(`${API_BASE}/user/find-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, birth, email }),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`비밀번호 찾기 실패 (${res.status}): ${msg}`);
  }
  try {
    return await res.json();
  } catch {
    return { status: 'success' };
  }
}

/**
 * ✅ 회원정보 수정
 * PATCH /user/edit
 * header: Authorization: Bearer <access_token>
 * body: { new_password?, new_affiliation?, delete_profile_image? }
 */
export async function editUser(
  accessToken: string,
  data: {
    new_password?: string;
    new_affiliation?: string;
    delete_profile_image?: boolean;
  }
): Promise<{
  changed_password: boolean;
  changed_profile_image: string | null;
  deleted_profile_image: boolean;
  changed_affiliation: string | null;
}> {
  const res = await fetch(`${API_BASE}/user/edit`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`정보 수정 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}
