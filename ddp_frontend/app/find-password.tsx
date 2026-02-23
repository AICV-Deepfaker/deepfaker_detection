import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import { useState } from 'react';
import {
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
import { findPassword } from '@/lib/account-api';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function FindPasswordScreen() {
  const insets = useSafeAreaInsets();
  const [name, setName] = useState('');
  const [birthdate, setBirthdate] = useState('');
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleFind = async () => {
    if (!name.trim() || !birthdate.trim() || !email.trim()) {
      Alert.alert('입력 오류', '이름, 생년월일, 이메일을 모두 입력해 주세요.');
      return;
    }
    setLoading(true);
    try {
      await findPassword(name.trim(), birthdate.trim(), email.trim());
      setSent(true);
    } catch (e: any) {
      Alert.alert('오류', e?.message ?? '일치하는 계정 정보를 찾을 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
        </TouchableOpacity>

        <ThemedText style={styles.title}>비밀번호 찾기</ThemedText>
        <ThemedText style={styles.subtitle}>
          가입 시 입력한 이름, 생년월일, 이메일을 입력하면{'\n'}
          임시 비밀번호를 이메일로 발송해 드립니다.
        </ThemedText>

        <View style={styles.form}>
          <ThemedText style={styles.label}>이름</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="이름 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={name}
            onChangeText={(t) => { setName(t); setSent(false); }}
            editable={!loading && !sent}
          />

          <ThemedText style={[styles.label, { marginTop: 16 }]}>생년월일</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="예: 1990-01-15"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={birthdate}
            onChangeText={(t) => { setBirthdate(t); setSent(false); }}
            keyboardType="numbers-and-punctuation"
            editable={!loading && !sent}
          />

          <ThemedText style={[styles.label, { marginTop: 16 }]}>이메일</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="example@email.com"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={email}
            onChangeText={(t) => { setEmail(t); setSent(false); }}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            editable={!loading && !sent}
          />

          <TouchableOpacity
            style={[styles.primaryButton, (loading || sent) && styles.buttonDisabled]}
            onPress={handleFind}
            disabled={loading || sent}
            activeOpacity={0.8}>
            <ThemedText style={styles.primaryButtonText}>
              {loading ? '확인 중...' : '임시 비밀번호 발송'}
            </ThemedText>
          </TouchableOpacity>

          {sent && (
            <View style={styles.resultBox}>
              <MaterialIcons name="check-circle" size={20} color={ACCENT_GREEN} />
              <View style={{ flex: 1 }}>
                <ThemedText style={styles.resultTitle}>이메일 발송 완료</ThemedText>
                <ThemedText style={styles.resultHint}>
                  임시 비밀번호가 <ThemedText style={{ fontWeight: '700' }}>{email}</ThemedText>으로 발송되었습니다.{'\n'}
                  로그인 후 마이페이지에서 비밀번호를 변경해 주세요.
                </ThemedText>
              </View>
            </View>
          )}

          <TouchableOpacity style={styles.backToLogin} onPress={() => router.replace('/login')} hitSlop={8}>
            <ThemedText style={styles.backToLoginText}>로그인으로 돌아가기</ThemedText>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scrollContent: { paddingHorizontal: 24, paddingTop: 12 },
  backButton: { alignSelf: 'flex-start', padding: 4, marginBottom: 24 },
  title: { fontSize: 24, fontWeight: '800', color: TEXT_COLOR, marginBottom: 8 },
  subtitle: { fontSize: 14, color: SECONDARY_TEXT_COLOR, marginBottom: 28, lineHeight: 20 },
  form: { width: '100%' },
  label: { fontSize: 14, fontWeight: '600', color: TEXT_COLOR, marginBottom: 8 },
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
  },
  buttonDisabled: { opacity: 0.6 },
  primaryButtonText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  resultBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginTop: 20,
    borderRadius: 12,
    padding: 16,
    backgroundColor: 'rgba(0,207,144,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(0,207,144,0.3)',
  },
  resultTitle: { fontSize: 14, fontWeight: '700', color: TEXT_COLOR, marginBottom: 6 },
  resultHint: { fontSize: 13, color: SECONDARY_TEXT_COLOR, lineHeight: 19 },
  backToLogin: { alignItems: 'center', marginTop: 28 },
  backToLoginText: { fontSize: 14, fontWeight: '600', color: ACCENT_GREEN },
});
