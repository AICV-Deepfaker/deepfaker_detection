import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
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

import { ThemedText } from '@/components/themed-text';
import { register } from '@/lib/account-api';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

// 백엔드 enum 기준: Affiliation = "개인" | "기관" | "회사"
type Affiliation = '개인' | '기관' | '회사';

const AFFILIATION_OPTIONS: { value: Affiliation; label: string }[] = [
  { value: '개인', label: '개인' },
  { value: '기관', label: '기관' },
  { value: '회사', label: '회사' },
];

export default function SignupScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [name, setName] = useState('');
  const [nickname, setNickname] = useState('');
  const [birthdate, setBirthdate] = useState('');
  const [profilePhotoUri, setProfilePhotoUri] = useState<string | null>(null);
  const [affiliation, setAffiliation] = useState<Affiliation | undefined>(undefined);
  const [loading, setLoading] = useState(false);

  const pickProfilePhoto = useCallback(async () => {
    const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!granted) {
      Alert.alert('권한 필요', '갤러리 접근 권한이 필요합니다.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      setProfilePhotoUri(result.assets[0].uri);
    }
  }, []);

  const handleSignup = useCallback(async () => {
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    const trimmedConfirm = passwordConfirm.trim();
    const trimmedName = name.trim();
    const trimmedNickname = nickname.trim();
    const trimmedBirthdate = birthdate.trim();

    if (!trimmedEmail || !trimmedPassword || !trimmedConfirm) {
      Alert.alert('입력 오류', '이메일과 비밀번호를 입력해 주세요.');
      return;
    }
    if (!trimmedName) {
      Alert.alert('입력 오류', '이름을 입력해 주세요.');
      return;
    }
    if (!trimmedNickname) {
      Alert.alert('입력 오류', '별명을 입력해 주세요.');
      return;
    }
    if (!trimmedBirthdate) {
      Alert.alert('입력 오류', '생년월일을 입력해 주세요.');
      return;
    }
    if (trimmedPassword.length < 8) {
      Alert.alert('입력 오류', '비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (trimmedPassword !== trimmedConfirm) {
      Alert.alert('입력 오류', '비밀번호가 일치하지 않습니다.');
      return;
    }

    setLoading(true);
    try {
      await register(
        {
          email: trimmedEmail,
          password: trimmedPassword,
          name: trimmedName,
          nickname: trimmedNickname,
          birth: trimmedBirthdate,
          affiliation: affiliation,
        },
        profilePhotoUri
      );
      Alert.alert('회원가입 완료', '로그인해 주세요.', [
        { text: '확인', onPress: () => router.replace('/login') },
      ]);
    } catch (e: any) {
      Alert.alert('회원가입 실패', e?.message ?? '다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  }, [email, password, passwordConfirm, name, nickname, birthdate, profilePhotoUri, affiliation]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}>
      <ScrollView
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
        </TouchableOpacity>

        <View style={styles.logoWrap}>
          <Image
            source={require('@/assets/images/ddp_applogo.png')}
            style={styles.logo}
            contentFit="contain"
          />
        </View>

        <View style={styles.form}>
          <ThemedText style={styles.sectionLabel}>이메일 *</ThemedText>
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
          <ThemedText style={[styles.sectionLabel, { marginTop: 16 }]}>비밀번호 * (8자 이상)</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="8자 이상 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            editable={!loading}
          />
          <ThemedText style={[styles.sectionLabel, { marginTop: 16 }]}>비밀번호 확인 *</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="비밀번호 다시 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={passwordConfirm}
            onChangeText={setPasswordConfirm}
            secureTextEntry
            editable={!loading}
          />

          <ThemedText style={[styles.sectionLabel, { marginTop: 20 }]}>이름 * (2자 이상)</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="이름 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={name}
            onChangeText={setName}
            editable={!loading}
          />
          <ThemedText style={[styles.sectionLabel, { marginTop: 16 }]}>별명 *</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="홈에 표시될 별명"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={nickname}
            onChangeText={setNickname}
            editable={!loading}
          />
          <ThemedText style={[styles.sectionLabel, { marginTop: 16 }]}>생년월일 *</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="예: 1990-01-15"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={birthdate}
            onChangeText={setBirthdate}
            keyboardType="numbers-and-punctuation"
            editable={!loading}
          />

          <ThemedText style={[styles.sectionLabel, { marginTop: 20 }]}>프로필 사진 (선택)</ThemedText>
          <TouchableOpacity style={styles.photoButton} onPress={pickProfilePhoto} disabled={loading}>
            {profilePhotoUri ? (
              <Image source={{ uri: profilePhotoUri }} style={styles.photoPreview} contentFit="cover" />
            ) : (
              <View style={styles.photoPlaceholder}>
                <MaterialIcons name="add-a-photo" size={32} color={SECONDARY_TEXT_COLOR} />
                <ThemedText style={styles.photoPlaceholderText}>사진 추가</ThemedText>
              </View>
            )}
          </TouchableOpacity>

          <ThemedText style={[styles.sectionLabel, { marginTop: 20 }]}>소속 (선택)</ThemedText>
          <View style={styles.affiliationRow}>
            {AFFILIATION_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                style={[styles.affiliationChip, affiliation === opt.value && styles.affiliationChipSelected]}
                onPress={() => setAffiliation(affiliation === opt.value ? undefined : opt.value)}
                disabled={loading}>
                <ThemedText style={[styles.affiliationLabel, affiliation === opt.value && styles.affiliationLabelSelected]}>
                  {opt.label}
                </ThemedText>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={[styles.primaryButton, loading && styles.primaryButtonDisabled]}
            onPress={handleSignup}
            disabled={loading}
            activeOpacity={0.8}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText style={styles.primaryButtonText}>회원가입</ThemedText>
            )}
          </TouchableOpacity>

          <View style={styles.loginRow}>
            <ThemedText style={styles.loginHint}>이미 계정이 있으신가요? </ThemedText>
            <TouchableOpacity onPress={() => router.back()} hitSlop={8}>
              <ThemedText style={styles.loginLink}>로그인</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scrollContent: { paddingHorizontal: 24, paddingTop: 12 },
  backButton: { alignSelf: 'flex-start', padding: 4, marginBottom: 8 },
  logoWrap: { alignItems: 'center', marginBottom: 24 },
  logo: { width: 300, height: 140 },
  form: { width: '100%' },
  sectionLabel: { fontSize: 14, fontWeight: '600', color: TEXT_COLOR, marginBottom: 8 },
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
  photoButton: { alignSelf: 'flex-start' },
  photoPlaceholder: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#F0F0F0',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
  },
  photoPlaceholderText: { fontSize: 12, color: SECONDARY_TEXT_COLOR, marginTop: 4 },
  photoPreview: { width: 88, height: 88, borderRadius: 44 },
  affiliationRow: { flexDirection: 'row', gap: 10, flexWrap: 'wrap' },
  affiliationChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#F0F0F0',
  },
  affiliationChipSelected: { backgroundColor: ACCENT_GREEN },
  affiliationLabel: { fontSize: 14, fontWeight: '600', color: SECONDARY_TEXT_COLOR },
  affiliationLabelSelected: { color: '#fff' },
  primaryButton: {
    backgroundColor: ACCENT_GREEN,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 28,
    minHeight: 52,
  },
  primaryButtonDisabled: { opacity: 0.7 },
  primaryButtonText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  loginRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 24 },
  loginHint: { fontSize: 14, color: SECONDARY_TEXT_COLOR },
  loginLink: { fontSize: 14, fontWeight: '700', color: ACCENT_GREEN },
});
