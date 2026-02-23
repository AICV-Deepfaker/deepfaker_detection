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
import { setAuth } from '@/lib/auth-storage';
import { login } from '@/lib/account-api';

// Expo Go에서 WebBrowser 세션을 완료하기 위해 필요
WebBrowser.maybeCompleteAuthSession();

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || '';
const EXPO_OWNER = process.env.EXPO_PUBLIC_EXPO_OWNER || '';

// Google OAuth 전체 discovery 문서 (tokenEndpoint 필수 — 없으면 proxy가 code 교환 실패)
const GOOGLE_DISCOVERY = {
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
  tokenEndpoint: 'https://oauth2.googleapis.com/token',
  revocationEndpoint: 'https://oauth2.googleapis.com/revoke',
  userInfoEndpoint: 'https://openidconnect.googleapis.com/v1/userinfo',
};

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // auth.expo.io 프록시: Google이 code를 프록시로 보내고, 앱은 useProxy:true로 결과를 polling
  const redirectUri = `https://auth.expo.io/@${EXPO_OWNER.trim()}/ddp`;

  // useProxy는 v7 타입에서 제거됐으나 런타임에선 동작 (auth.expo.io polling에 필요)
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  const [, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: GOOGLE_WEB_CLIENT_ID,
      scopes: ['openid', 'profile', 'email'],
      redirectUri,
      useProxy: true,
    },
    GOOGLE_DISCOVERY
  );

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
        // 서버 연결 된 경우 이 코드로 변경
//       const result = await login(trimmedEmail, trimmedPassword);
//
//           await setAuth({
//             email: result.email,
//             nickname: result.nickname,
//             accessToken: result.access_token,
//             refreshToken: result.refresh_token,
//             userId: result.user_id,
//             isLoggedIn: true,
//           });
//
//           router.replace('/(tabs)');
//         } catch (e: any) {
//           Alert.alert('로그인 실패', e?.message ?? '다시 시도해 주세요.');
//         } finally {
//           setLoading(false);
//         }
//       }, [email, password]);

      // 임시로 사용: 서버 붙기 전까지는 로컬 로그인으로 통과
      await setAuth({
            email: trimmedEmail,
            nickname: trimmedEmail.split('@')[0],
            isLoggedIn: true,
            accessToken: 'local-dev',
            refreshToken: 'local-dev',
            userId: 0,
          } as any);

          router.replace('/(tabs)');
        } catch (e) {
          console.log('LOGIN ERROR:', e);
          Alert.alert('오류', '로그인 처리 중 오류가 발생했습니다.');
        } finally {
          setLoading(false);
        }
      }, [email, password]);

  const handleGoogleLogin = useCallback(() => {
    if (!GOOGLE_WEB_CLIENT_ID) {
      Alert.alert('설정 필요', 'Google Client ID가 설정되지 않았습니다.');
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
