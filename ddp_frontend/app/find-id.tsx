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
import { findId } from '@/lib/account-api';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function FindIdScreen() {
  const insets = useSafeAreaInsets();
  const [name, setName] = useState('');
  const [birthdate, setBirthdate] = useState('');
  const [foundEmail, setFoundEmail] = useState<string | null | undefined>(undefined);
  const [loading, setLoading] = useState(false);

  const handleFind = async () => {
    if (!name.trim() || !birthdate.trim()) {
      Alert.alert('입력 오류', '이름과 생년월일을 입력해 주세요.');
      return;
    }
    setLoading(true);
    try {
      const result = await findId(name.trim(), birthdate.trim());
      setFoundEmail(result.email);
    } catch (e: any) {
      // 404 or 404-like → 일치하는 계정 없음
      setFoundEmail(null);
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

        <ThemedText style={styles.title}>아이디 찾기</ThemedText>
        <ThemedText style={styles.subtitle}>가입 시 입력한 이름과 생년월일을 입력해 주세요.</ThemedText>

        <View style={styles.form}>
          <ThemedText style={styles.label}>이름</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="이름 입력"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={name}
            onChangeText={setName}
            editable={!loading}
          />

          <ThemedText style={[styles.label, { marginTop: 16 }]}>생년월일</ThemedText>
          <TextInput
            style={styles.input}
            placeholder="예: 1990-01-15"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={birthdate}
            onChangeText={setBirthdate}
            keyboardType="numbers-and-punctuation"
            editable={!loading}
          />

          <TouchableOpacity
            style={[styles.primaryButton, loading && styles.buttonDisabled]}
            onPress={handleFind}
            disabled={loading}
            activeOpacity={0.8}>
            <ThemedText style={styles.primaryButtonText}>아이디 찾기</ThemedText>
          </TouchableOpacity>

          {foundEmail !== undefined && (
            <View style={[styles.resultBox, foundEmail ? styles.resultSuccess : styles.resultFail]}>
              {foundEmail ? (
                <>
                  <MaterialIcons name="check-circle" size={20} color={ACCENT_GREEN} />
                  <View style={{ flex: 1 }}>
                    <ThemedText style={styles.resultLabel}>가입된 이메일</ThemedText>
                    <ThemedText style={styles.resultEmail}>{foundEmail}</ThemedText>
                  </View>
                </>
              ) : (
                <>
                  <MaterialIcons name="error-outline" size={20} color="#E53935" />
                  <ThemedText style={styles.resultFailText}>
                    일치하는 계정을 찾을 수 없습니다.
                  </ThemedText>
                </>
              )}
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
  buttonDisabled: { opacity: 0.7 },
  primaryButtonText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  resultBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginTop: 20,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
  },
  resultSuccess: { backgroundColor: 'rgba(0,207,144,0.06)', borderColor: 'rgba(0,207,144,0.3)' },
  resultFail: { backgroundColor: 'rgba(229,57,53,0.06)', borderColor: 'rgba(229,57,53,0.3)' },
  resultLabel: { fontSize: 12, color: SECONDARY_TEXT_COLOR, marginBottom: 2 },
  resultEmail: { fontSize: 16, fontWeight: '700', color: TEXT_COLOR },
  resultFailText: { fontSize: 14, color: '#E53935', fontWeight: '600' },
  backToLogin: { alignItems: 'center', marginTop: 28 },
  backToLoginText: { fontSize: 14, fontWeight: '600', color: ACCENT_GREEN },
});
