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

/** URI에서 FormData용 파일 객체 생성 */
function uriToFormFile(uri: string) {
  const filename = uri.split('/').pop() ?? 'image.jpg';
  const match = /\.(\w+)$/.exec(filename);
  const type = match ? `image/${match[1].toLowerCase()}` : 'image/jpeg';
  return { uri, name: filename, type } as unknown as Blob;
}

/**
 * ✅ 로그인
 * POST /auth/login
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

  try {
    return await res.json();
  } catch {
    return { status: 'success' };
  }
}

/**
 * ✅ 토큰 재발급
 * POST /auth/reissue
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
 * POST /user/register  (multipart/form-data)
 * @param profileImageUri 선택적 프로필 이미지 로컬 URI
 */
export type UserRegisterRequest = {
  email: string;
  password: string;
  name: string;
  nickname: string;
  birth?: string;       // "YYYY-MM-DD"
  affiliation?: string; // "개인" | "기관" | "회사"
};

export type UserRegisterResponse = {
  user_id: string;
  email: string;
  name: string;
  nickname: string;
  created_at: string;
};

export async function register(
  data: UserRegisterRequest,
  _profileImageUri?: string | null
): Promise<UserRegisterResponse> {
  const body: Record<string, unknown> = {
    email: data.email,
    password: data.password,
    name: data.name,
    nickname: data.nickname,
  };
  if (data.birth) body.birth = data.birth;
  if (data.affiliation) body.affiliation = data.affiliation;

  const res = await fetch(`${API_BASE}/user/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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
 * PATCH /user/edit  (multipart/form-data)
 * @param profileImageUri 새 프로필 이미지 로컬 URI (변경할 경우에만 전달)
 */
export type UserEditRequest = {
  new_password?: string;
  new_affiliation?: string;
};

export type UserEditResponse = {
  changed_password: boolean;
  latest_user_info: {
    user_id: string;
    email: string;
    name: string;
    nickname: string;
    birth: string | null;
    affiliation: string | null;
    profile_image: string | null;
    created_at: string;
  };
};

export async function editUser(
  accessToken: string,
  data: UserEditRequest,
  profileImageUri?: string | null
): Promise<UserEditResponse> {
  const formData = new FormData();
  if (data.new_password) formData.append('new_password', data.new_password);
  if (data.new_affiliation) formData.append('new_affiliation', data.new_affiliation);
  if (profileImageUri) {
    formData.append('new_profile_image', uriToFormFile(profileImageUri));
  }

  const res = await fetch(`${API_BASE}/user/edit`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`정보 수정 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}

/**
 * GET /user/me - 내 정보 조회 (토큰 필요)
 */
export async function getMyProfile(accessToken: string): Promise<{
  user_id: string;
  email: string;
  name: string;
  nickname: string;
  birth: string | null;
  affiliation: string | null;
  profile_image: string | null;
  created_at: string;
}> {
  const res = await fetch(`${API_BASE}/user/me`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!res.ok) {
    const msg = await readErrorText(res);
    throw new Error(`내 정보 조회 실패 (${res.status}): ${msg}`);
  }
  return res.json();
}
