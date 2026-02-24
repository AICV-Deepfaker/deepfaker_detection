import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';

import { ThemedText } from '@/components/themed-text';
import { setAuth } from '@/lib/auth-storage';
import { login } from '@/lib/account-api';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');

/** ddp://auth?key=val&... 형태의 deep link URL에서 파라미터를 파싱 */
function parseDeepLinkParams(url: string): Record<string, string> {
  const query = url.split('?')[1] ?? '';
  const params: Record<string, string> = {};
  for (const part of query.split('&')) {
    const eqIdx = part.indexOf('=');
    if (eqIdx === -1) continue;
    params[part.slice(0, eqIdx)] = decodeURIComponent(part.slice(eqIdx + 1));
  }
  return params;
}

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleLogin = useCallback(async () => {
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    if (!trimmedEmail || !trimmedPassword) {
      Alert.alert('입력 오류', '이메일과 비밀번호를 입력해 주세요.');
      return;
    }

    setLoading(true);
    try {
      const result = await login(trimmedEmail, trimmedPassword);
      await setAuth({
        email: result.email,
        nickname: result.nickname,
        accessToken: result.access_token,
        refreshToken: result.refresh_token,
        userId: result.user_id,
        isLoggedIn: true,
      });
      router.replace('/(tabs)');
    } catch (e: any) {
      Alert.alert('로그인 실패', e?.message ?? '다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  }, [email, password]);

  const handleGoogleLogin = useCallback(async () => {
    if (!API_BASE) {
      Alert.alert('설정 오류', 'API URL이 설정되지 않았습니다.');
      return;
    }
    setGoogleLoading(true);
    try {
      // Expo Go: exp://192.168.x.x:8081/--/auth, 빌드: ddp://auth
      const appRedirectUri = Linking.createURL('auth');

      // 백엔드의 서버 사이드 Google OAuth 시작
      // 서버가 Google → callback → appRedirectUri?access_token=...&refresh_token=... 로 redirect
      const result = await WebBrowser.openAuthSessionAsync(
        `${API_BASE}/auth/google?app_redirect=${encodeURIComponent(appRedirectUri)}`,
        appRedirectUri
      );

      if (result.type === 'success') {
        const p = parseDeepLinkParams(result.url);

        // 서버에서 error 파라미터를 보낸 경우 (code 재사용 등)
        if (p.error) {
          Alert.alert('Google 로그인 실패', decodeURIComponent(p.error));
          return;
        }

        const { access_token, refresh_token, user_id, email: userEmail, nickname } = p;

        if (!access_token || !refresh_token || !user_id || !userEmail) {
          Alert.alert('Google 로그인 실패', '인증 정보를 받지 못했습니다.');
          return;
        }

        await setAuth({
          email: userEmail,
          nickname: nickname || undefined,
          accessToken: access_token,
          refreshToken: refresh_token,
          userId: parseInt(user_id, 10),
          isLoggedIn: true,
        });
        router.replace('/(tabs)');
      } else if (result.type === 'cancel') {
        // 사용자가 직접 취소 - 아무 동작 없음
      }
    } catch (e: any) {
      Alert.alert('Google 로그인 실패', e?.message ?? '다시 시도해 주세요.');
    } finally {
      setGoogleLoading(false);
    }
  }, []);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}>
      <ScrollView
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        {/* 로고 */}
        <View style={styles.logoWrap}>
          <Image
            source={require('@/assets/images/ddp_applogo.png')}
            style={styles.logo}
            contentFit="contain"
          />
        </View>

        <View style={styles.form}>
          <ThemedText style={styles.sectionLabel}>이메일</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="example@email.com"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            editable={!loading}
          />
          <ThemedText style={[styles.sectionLabel, { marginTop: 16 }]}>비밀번호</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="비밀번호 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.primaryButton, loading && styles.primaryButtonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.8}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.primaryButtonText}>로그인</ThemedText>
            )}
          </TouchableOpacity>

          <View style={styles.dividerWrap}>
            <View style={styles.dividerLine} />
            <ThemedText style={styles.dividerText}>또는</ThemedText>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity
            style={[styles.googleButton, googleLoading && styles.primaryButtonDisabled]}
            onPress={handleGoogleLogin}
            disabled={googleLoading}
            activeOpacity={0.8}>
            {googleLoading ? (
              <ActivityIndicator color={TEXT_COLOR} />
            ) : (
              <>
                <MaterialIcons name="g-translate" size={22} color={TEXT_COLOR} />
                <ThemedText style={styles.googleButtonText}>Google로 로그인</ThemedText>
              </>
            )}
          </TouchableOpacity>

          <View style={styles.findRow}>
            <TouchableOpacity onPress={() => router.push('/find-id')} hitSlop={8}>
              <ThemedText style={styles.findLink}>아이디 찾기</ThemedText>
            </TouchableOpacity>
            <ThemedText style={styles.findSep}>|</ThemedText>
            <TouchableOpacity onPress={() => router.push('/find-password')} hitSlop={8}>
              <ThemedText style={styles.findLink}>비밀번호 찾기</ThemedText>
            </TouchableOpacity>
          </View>

          <View style={styles.signupRow}>
            <ThemedText style={styles.signupHint}>계정이 없으신가요? </ThemedText>
            <TouchableOpacity onPress={() => router.push('/signup')} hitSlop={8}>
              <ThemedText style={styles.signupLink}>회원가입</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  logoWrap: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logo: {
    width: 300,
    height: 140,
  },
  form: {
    width: '100%',
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: TEXT_COLOR,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  primaryButton: {
    backgroundColor: ACCENT_GREEN,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
    minHeight: 52,
  },
  primaryButtonDisabled: {
    opacity: 0.7,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  dividerWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 28,
    marginBottom: 28,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.1)',
  },
  dividerText: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginHorizontal: 16,
  },
  googleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingVertical: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.12)',
    minHeight: 52,
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: TEXT_COLOR,
  },
  findRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
    gap: 8,
  },
  findLink: {
    fontSize: 14,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
  },
  findSep: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
  },
  signupRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  signupHint: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
  },
  signupLink: {
    fontSize: 14,
    fontWeight: '700',
    color: ACCENT_GREEN,
  },
});
