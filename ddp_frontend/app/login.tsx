import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import * as AuthSession from 'expo-auth-session';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
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
import * as WebBrowser from 'expo-web-browser';

import { ThemedText } from '@/components/themed-text';
import { findStoredUser, setAuth } from '@/lib/auth-storage';
import * as Clipboard from 'expo-clipboard';

// WebBrowser must be warmed up for auth redirect on Android
WebBrowser.maybeCompleteAuthSession();

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

// Google Cloud Console에서 OAuth 2.0 클라이언트 ID (웹 앱) 발급 후
// .env에 EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=클라이언트ID 입력
// exp:// 가 Google에서 거부되면 EXPO_PUBLIC_EXPO_OWNER=Expo계정명 넣고
// 승인된 리디렉션 URI에 https://auth.expo.io/@계정명/ddp 등록 (docs 참고)
const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || '';
const EXPO_OWNER = process.env.EXPO_PUBLIC_EXPO_OWNER || '';

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // EXPO_OWNER가 있으면 https://auth.expo.io/@계정/ddp 사용 (Google이 .io 도메인만 허용할 때)
  // 없으면 makeRedirectUri 결과 사용 (Expo Go는 exp://... 나옴)
  const redirectUri =
    EXPO_OWNER.trim() !== ''
      ? `https://auth.expo.io/@${EXPO_OWNER.trim()}/ddp`
      : AuthSession.makeRedirectUri({
          scheme: 'ddp',
          path: 'redirect',
          useProxy: true,
        });

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: GOOGLE_WEB_CLIENT_ID,
      scopes: ['openid', 'profile', 'email'],
      redirectUri,
      useProxy: EXPO_OWNER.trim() !== '',
    },
    { authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth' }
  );

  useEffect(() => {
    if (__DEV__ && redirectUri) {
      console.log('[Redirect URI] Google에 등록할 값:', redirectUri);
    }
  }, [redirectUri]);

  useEffect(() => {
    if (!response) return;
    if (response.type === 'success') {
      setGoogleLoading(false);
      setAuth({ email: 'google', isLoggedIn: true }).then(() => router.replace('/(tabs)'));
    } else if (response.type === 'error') {
      setGoogleLoading(false);
      Alert.alert('Google 로그인 실패', response.error?.message || '다시 시도해 주세요.');
    } else if (response.type === 'dismiss') {
      setGoogleLoading(false);
    }
  }, [response]);

  const handleLogin = useCallback(async () => {
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    if (!trimmedEmail || !trimmedPassword) {
      Alert.alert('입력 오류', '이메일과 비밀번호를 입력해 주세요.');
      return;
    }
    setLoading(true);
    try {
      const user = await findStoredUser(trimmedEmail, trimmedPassword);
      await setAuth({
        email: trimmedEmail,
        isLoggedIn: true,
        nickname: user?.nickname,
      });
      router.replace('/(tabs)');
    } catch {
      Alert.alert('오류', '로그인 처리 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [email, password]);

  const handleGoogleLogin = useCallback(() => {
    if (!GOOGLE_WEB_CLIENT_ID) {
      Alert.alert(
        '설정 필요',
        'Google 로그인을 위해 Google Cloud Console에서 OAuth 클라이언트 ID를 발급한 뒤,\n환경변수 EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID에 넣어 주세요.'
      );
      return;
    }
    setGoogleLoading(true);
    promptAsync();
  }, [promptAsync]);

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

          {/* Google Console "승인된 리디렉션 URI"에 등록할 값 (복사용) */}
          <TouchableOpacity
            style={styles.redirectUriWrap}
            onPress={() => {
              Clipboard.setStringAsync(redirectUri);
              Alert.alert('복사됨', '리디렉션 URI가 클립보드에 복사되었습니다. Google Console에 붙여넣으세요.');
            }}
            activeOpacity={0.8}>
            <ThemedText style={styles.redirectUriLabel}>리디렉션 URI (Google에 등록할 값)</ThemedText>
            <ThemedText style={styles.redirectUriValue} numberOfLines={2} selectable>
              {redirectUri}
            </ThemedText>
            <ThemedText style={styles.redirectUriHint}>탭하면 복사</ThemedText>
          </TouchableOpacity>

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
  redirectUriWrap: {
    marginTop: 20,
    paddingVertical: 12,
    paddingHorizontal: 14,
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  redirectUriLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 6,
  },
  redirectUriValue: {
    fontSize: 13,
    color: TEXT_COLOR,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  redirectUriHint: {
    fontSize: 11,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 6,
  },
  signupRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 28,
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
