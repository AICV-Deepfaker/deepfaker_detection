import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import * as Clipboard from 'expo-clipboard';
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
import { getProfileByEmail, updateUserPassword } from '@/lib/auth-storage';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

function generateTempPassword(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  let result = '';
  for (let i = 0; i < 8; i++) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

export default function FindPasswordScreen() {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFind = async () => {
    const trimmed = email.trim();
    if (!trimmed) {
      Alert.alert('입력 오류', '이메일을 입력해 주세요.');
      return;
    }
    setLoading(true);
    try {
      const profile = await getProfileByEmail(trimmed);
      if (!profile) {
        Alert.alert('찾을 수 없음', '해당 이메일로 가입된 계정이 없습니다.');
        return;
      }
      const temp = generateTempPassword();
      const ok = await updateUserPassword(trimmed, temp);
      if (ok) {
        setTempPassword(temp);
      } else {
        Alert.alert('오류', '임시 비밀번호 발급에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!tempPassword) return;
    await Clipboard.setStringAsync(tempPassword);
    Alert.alert('복사됨', '임시 비밀번호가 클립보드에 복사되었습니다.');
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
          가입한 이메일을 입력하면 임시 비밀번호를 발급해 드립니다.
        </ThemedText>

        <View style={styles.form}>
          <ThemedText style={styles.label}>이메일</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="example@email.com"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={email}
            onChangeText={(t) => { setEmail(t); setTempPassword(null); }}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.primaryButton, (loading || !!tempPassword) && styles.buttonDisabled]}
            onPress={handleFind}
            disabled={loading || !!tempPassword}
            activeOpacity={0.8}>
            <ThemedText style={styles.primaryButtonText}>임시 비밀번호 발급</ThemedText>
          </TouchableOpacity>

          {tempPassword && (
            <View style={styles.resultBox}>
              <View style={styles.resultHeader}>
                <MaterialIcons name="check-circle" size={20} color={ACCENT_GREEN} />
                <ThemedText style={styles.resultTitle}>임시 비밀번호 발급 완료</ThemedText>
              </View>

              <View style={styles.passwordRow}>
                <ThemedText style={styles.passwordText}>{tempPassword}</ThemedText>
                <TouchableOpacity onPress={handleCopy} style={styles.copyButton} hitSlop={8}>
                  <MaterialIcons name="content-copy" size={20} color={ACCENT_GREEN} />
                </TouchableOpacity>
              </View>

              <ThemedText style={styles.hint}>
                이 비밀번호로 로그인 후, 마이 &gt; 회원정보에서 비밀번호를 변경해 주세요.
              </ThemedText>
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
    marginTop: 20,
    borderRadius: 12,
    padding: 16,
    backgroundColor: 'rgba(0,207,144,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(0,207,144,0.3)',
    gap: 12,
  },
  resultHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  resultTitle: { fontSize: 14, fontWeight: '700', color: TEXT_COLOR },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
  },
  passwordText: {
    flex: 1,
    fontSize: 20,
    fontWeight: '800',
    color: TEXT_COLOR,
    letterSpacing: 2,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  copyButton: { padding: 4 },
  hint: { fontSize: 13, color: SECONDARY_TEXT_COLOR, lineHeight: 18 },
  backToLogin: { alignItems: 'center', marginTop: 28 },
  backToLoginText: { fontSize: 14, fontWeight: '600', color: ACCENT_GREEN },
});
