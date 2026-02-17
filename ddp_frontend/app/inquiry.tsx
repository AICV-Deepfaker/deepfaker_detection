import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import React, { useCallback, useMemo, useState } from 'react';
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

const ACCENT_GREEN = '#00CF90';
const TEXT = '#111';
const SUB = '#687076';
const BORDER = 'rgba(0,0,0,0.08)';
const BG = '#fff';

type PickedFile = {
  name: string;
  uri: string;
  size?: number;
  mimeType?: string;
};

const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());

export default function InquiryScreen() {
  const insets = useSafeAreaInsets();

  const [content, setContent] = useState('');
  const [email, setEmail] = useState('');
  const [userId, setUserId] = useState('');
  const [school, setSchool] = useState('');
  const [agree, setAgree] = useState(false);
  const [file, setFile] = useState<PickedFile | null>(null);

  const canSubmit = useMemo(() => {
    if (!agree) return false;
    if (!content.trim()) return false;
    if (!email.trim() || !isEmail(email)) return false;
    if (!userId.trim()) return false;
    return true;
  }, [agree, content, email, userId]);

  const pickFile = useCallback(async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({
        copyToCacheDirectory: true,
        multiple: false,
        type: '*/*',
      });

      if (res.canceled) return;

      const a = res.assets?.[0];
      if (!a) return;

      setFile({
        name: a.name ?? '첨부파일',
        uri: a.uri,
        size: a.size,
        mimeType: a.mimeType,
      });
    } catch (e) {
      Alert.alert('파일 선택 실패', e instanceof Error ? e.message : '다시 시도해 주세요.');
    }
  }, []);

  const onSubmit = useCallback(() => {
    if (!canSubmit) {
      Alert.alert(
        '입력 확인',
        '필수 항목을 확인해 주세요.\n- 내용\n- 이메일(형식)\n- 이용자 아이디\n- 개인정보 동의(필수)'
      );
      return;
    }

    // ✅ 여기서 서버/메일 연동 예정
    // 지금은 접수 완료 UI만
    Alert.alert('접수 완료', '문의가 접수되었습니다.\n입력하신 이메일로 답변드릴게요.', [
      {
        text: '확인',
        onPress: () => router.back(),
      },
    ]);
  }, [canSubmit]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>문의하기</ThemedText>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn} hitSlop={12}>
          <MaterialIcons name="close" size={24} color={TEXT} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* 내용 */}
        <ThemedText style={styles.label}>내용</ThemedText>
        <View style={styles.textareaCard}>
          <TextInput
            value={content}
            onChangeText={setContent}
            placeholder="문의 내용을 입력해 주세요."
            placeholderTextColor={SUB}
            style={styles.textarea}
            multiline
            textAlignVertical="top"
          />
        </View>

        {/* 파일 첨부 */}
        <ThemedText style={[styles.label, { marginTop: 18 }]}>파일 첨부</ThemedText>
        <TouchableOpacity style={styles.fileBtn} activeOpacity={0.85} onPress={pickFile}>
          <View style={styles.fileBtnLeft}>
            <MaterialIcons name="attach-file" size={20} color={ACCENT_GREEN} />
            <ThemedText style={styles.fileBtnText}>파일 선택</ThemedText>
          </View>
          <MaterialIcons name="chevron-right" size={22} color={SUB} />
        </TouchableOpacity>

        {file && (
          <View style={styles.fileMeta}>
            <ThemedText style={styles.fileName} numberOfLines={1}>
              {file.name}
            </ThemedText>
            <TouchableOpacity onPress={() => setFile(null)} hitSlop={10}>
              <MaterialIcons name="close" size={18} color={SUB} />
            </TouchableOpacity>
          </View>
        )}

        {/* 연락받을 이메일 */}
        <ThemedText style={[styles.label, { marginTop: 18 }]}>연락받을 이메일</ThemedText>
        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="example@email.com"
          placeholderTextColor={SUB}
          style={styles.input}
          autoCapitalize="none"
          keyboardType="email-address"
        />

        {/* 이용자 아이디 */}
        <ThemedText style={[styles.label, { marginTop: 18 }]}>이용자 아이디</ThemedText>
        <TextInput
          value={userId}
          onChangeText={setUserId}
          placeholder="아이디 입력"
          placeholderTextColor={SUB}
          style={styles.input}
          autoCapitalize="none"
        />

        {/* 개인정보 수집 및 이용 */}
        <ThemedText style={[styles.sectionTitle, { marginTop: 26 }]}>개인정보 수집 및 이용</ThemedText>

        <TouchableOpacity
          style={styles.agreeRow}
          activeOpacity={0.85}
          onPress={() => setAgree((p) => !p)}
        >
          <View style={[styles.checkbox, agree && styles.checkboxChecked]}>
            {agree && <MaterialIcons name="check" size={18} color="#fff" />}
          </View>
          <ThemedText style={styles.agreeText}>개인정보 수집 및 이용 동의 (필수)</ThemedText>
        </TouchableOpacity>

        <View style={styles.privacyBox}>
          <ThemedText style={styles.privacyText}>
            문의 처리를 위해 이메일, 문의내용에 포함된 개인정보를 수집하며, 개인정보처리방침에 따라{' '}
            <ThemedText style={styles.privacyBold}>3년 후 파기</ThemedText>됩니다.{'\n'}
            개인정보 수집 및 이용을 거부할 수 있으며, 거부할 경우 문의가 불가합니다.
          </ThemedText>
        </View>

        {/* 접수하기 */}
        <TouchableOpacity
          style={[styles.submitBtn, !canSubmit && styles.submitBtnDisabled]}
          activeOpacity={0.9}
          onPress={onSubmit}
        >
          <ThemedText style={styles.submitText}>접수하기</ThemedText>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: BG },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: BORDER,
    backgroundColor: '#fff',
  },
  headerBtn: { padding: 6 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: TEXT },

  scroll: { flex: 1, paddingHorizontal: 18, paddingTop: 14 },

  label: { fontSize: 13, fontWeight: '700', color: SUB, marginBottom: 10 },

  textareaCard: {
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 16,
    backgroundColor: '#fff',
    padding: 12,
  },
  textarea: {
    minHeight: 180,
    fontSize: 15,
    color: TEXT,
    lineHeight: 22,
  },

  fileBtn: {
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  fileBtnLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  fileBtnText: { fontSize: 15, fontWeight: '800', color: TEXT },

  fileMeta: {
    marginTop: 10,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: '#F8FAF9',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  fileName: { flex: 1, marginRight: 10, color: TEXT, fontWeight: '700' },

  input: {
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 14,
    backgroundColor: '#fff',
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 15,
    color: TEXT,
  },

  sectionTitle: { fontSize: 18, fontWeight: '900', color: TEXT, marginBottom: 12 },

  agreeRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10 },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: { backgroundColor: ACCENT_GREEN, borderColor: ACCENT_GREEN },
  agreeText: { fontSize: 14, fontWeight: '700', color: TEXT },

  privacyBox: {
    marginTop: 12,
    padding: 16,
    borderRadius: 16,
    backgroundColor: '#F6F7F8',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
  },
  privacyText: {
    fontSize: 14,
    lineHeight: 22,
    color: '#6B7280',
    fontWeight: '600',
  },
  privacyBold: {
    fontWeight: '700',
    color: '#111',
  },

  submitBtn: {
    marginTop: 18,
    backgroundColor: ACCENT_GREEN,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitBtnDisabled: { opacity: 0.4 },
  submitText: { color: '#fff', fontSize: 16, fontWeight: '900' },
});