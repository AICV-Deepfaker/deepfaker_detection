import AsyncStorage from '@react-native-async-storage/async-storage';

const AUTH_KEY = 'ddp_auth';
const USERS_KEY = 'ddp_users';

export type AuthUser = {
  email: string;
  nickname?: string;
  accessToken: string;
  refreshToken: string;
  userId: number;
  isLoggedIn: true;
};

export async function getAuth(): Promise<AuthUser | null> {
  try {
    const raw = await AsyncStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as AuthUser;
    return data?.isLoggedIn ? data : null;
  } catch {
    return null;
  }
}

export async function setAuth(user: AuthUser): Promise<void> {
  await AsyncStorage.setItem(AUTH_KEY, JSON.stringify(user));
}

export async function clearAuth(): Promise<void> {
  await AsyncStorage.removeItem(AUTH_KEY);
}

export type Affiliation = '개인' | '기관' | '기업';

export type StoredUser = {
  email: string;
  password: string;
  name?: string;
  nickname?: string;
  birthdate?: string;
  profilePhotoUri?: string;
  affiliation?: Affiliation;
};

export async function getStoredUsers(): Promise<StoredUser[]> {
  try {
    const raw = await AsyncStorage.getItem(USERS_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export async function addStoredUser(user: {
  email: string;
  password: string;
  name: string;
  nickname: string;
  birthdate: string;
  profilePhotoUri?: string;
  affiliation?: Affiliation;
}): Promise<void> {
  const users = await getStoredUsers();
  const filtered = users.filter((u) => u.email.toLowerCase() !== user.email.trim().toLowerCase());
  filtered.push({
    email: user.email.trim(),
    password: user.password,
    name: user.name.trim(),
    nickname: user.nickname.trim(),
    birthdate: user.birthdate.trim(),
    profilePhotoUri: user.profilePhotoUri,
    affiliation: user.affiliation,
  });
  await AsyncStorage.setItem(USERS_KEY, JSON.stringify(filtered));
}

export async function findStoredUser(email: string, password: string): Promise<StoredUser | null> {
  const users = await getStoredUsers();
  const found = users.find(
    (u) => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
  );
  return found ?? null;
}

export async function getProfileByEmail(email: string): Promise<StoredUser | null> {
  const users = await getStoredUsers();
  return users.find((u) => u.email.toLowerCase() === email.trim().toLowerCase()) ?? null;
}

export async function findUserByNameAndBirthdate(name: string, birthdate: string): Promise<string | null> {
  const users = await getStoredUsers();
  const found = users.find(
    (u) =>
      u.name?.trim().toLowerCase() === name.trim().toLowerCase() &&
      u.birthdate?.trim() === birthdate.trim()
  );
  return found?.email ?? null;
}

export async function updateUserPassword(email: string, newPassword: string): Promise<boolean> {
  try {
    const users = await getStoredUsers();
    const idx = users.findIndex((u) => u.email.toLowerCase() === email.trim().toLowerCase());
    if (idx === -1) return false;
    users[idx] = { ...users[idx], password: newPassword };
    await AsyncStorage.setItem(USERS_KEY, JSON.stringify(users));
    return true;
  } catch {
    return false;
  }
}

export async function updateUserProfile(
  email: string,
  updates: { affiliation?: Affiliation; profilePhotoUri?: string }
): Promise<boolean> {
  try {
    const users = await getStoredUsers();
    const idx = users.findIndex((u) => u.email.toLowerCase() === email.trim().toLowerCase());
    if (idx === -1) return false;
    users[idx] = { ...users[idx], ...updates };
    await AsyncStorage.setItem(USERS_KEY, JSON.stringify(users));
    return true;
  } catch {
    return false;
  }
}
