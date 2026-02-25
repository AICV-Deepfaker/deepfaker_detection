import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import {
  getAuth,
  type Affiliation,
} from '@/lib/auth-storage';
import { deleteProfileImage, editUser, getMyProfile } from '@/lib/account-api';
import { withAuth } from '@/lib/with-auth';

const ACCENT_GREEN = '#00CF90';
const TEXT = '#111';
const SUB = '#687076';
const CARD_BG = '#fff';
const BORDER = 'rgba(0,0,0,0.06)';
const ERROR_RED = '#E53935';

const AFFILIATION_OPTIONS: { value: Affiliation; label: string }[] = [
  { value: '개인', label: '개인' },
  { value: '기관', label: '기관' },
  { value: '회사', label: '회사' },
];

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <View style={styles.row}>
      <ThemedText style={styles.rowLabel}>{label}</ThemedText>
      <ThemedText style={styles.rowValue}>{value && value.trim() !== '' ? value : '-'}</ThemedText>
    </View>
  );
}

export default function MemberInfoScreen() {
  const insets = useSafeAreaInsets();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  type MyProfile = Awaited<ReturnType<typeof getMyProfile>>;
  const [profile, setProfile] = useState<MyProfile | null>(null);

  // 편집 모드
  const [editMode, setEditMode] = useState(false);
  const [editAffiliation, setEditAffiliation] = useState<Affiliation | undefined>(undefined);
  const [editPhotoUri, setEditPhotoUri] = useState<string | null>(null);

  // 프로필 이미지 삭제
  const [deleting, setDeleting] = useState(false);

  // 비밀번호 변경
  const [newPw, setNewPw] = useState('');
  const [newPwConfirm, setNewPwConfirm] = useState('');
  const [pwChanging, setPwChanging] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const auth = await getAuth();
      const email = auth?.email ?? null;
      setAuthEmail(email);
      if (!email || !auth?.accessToken) { setProfile(null); return; }
      // access_token 만료 시 refresh_token으로 자동 재발급 후 재시도
      const p = await withAuth((token) => getMyProfile(token));
      setProfile(p);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const enterEditMode = () => {
    if (!profile) return;
    setEditAffiliation((profile.affiliation as Affiliation) ?? undefined);
    setEditPhotoUri(profile.profile_image ?? null);
    setNewPw('');
    setNewPwConfirm('');
    setEditMode(true);
  };

  const cancelEditMode = () => {
    setEditMode(false);
  };

  const handleDeletePhoto = () => {
    Alert.alert('사진 삭제', '프로필 사진을 삭제하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          setDeleting(true);
          try {
            await withAuth((token) => deleteProfileImage(token));
            await load();
            setEditMode(false);
          } catch (e: any) {
            Alert.alert('오류', e?.message ?? '삭제에 실패했습니다.');
          } finally {
            setDeleting(false);
          }
        },
      },
    ]);
  };

  const pickPhoto = async () => {
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
      setEditPhotoUri(result.assets[0].uri);
    }
  };

  const handleSaveProfile = async () => {
    if (!authEmail) return;
    setSaving(true);
    // 기존 S3 URL과 다른 로컬 URI일 때만 업로드
    const hasNewPhoto = !!editPhotoUri && editPhotoUri !== profile?.profile_image;
    try {
      await withAuth((token) =>
        editUser(
          token,
          { new_affiliation: editAffiliation },
          hasNewPhoto ? editPhotoUri : undefined
        )
      );
      await load();
      setEditMode(false);
      Alert.alert('저장 완료', '프로필이 업데이트되었습니다.');
    } catch (e: any) {
      Alert.alert('오류', e?.message ?? '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!authEmail) return;
    if (!newPw || !newPwConfirm) {
      Alert.alert('입력 오류', '새 비밀번호를 입력해 주세요.');
      return;
    }
    if (newPw.length < 8) {
      Alert.alert('입력 오류', '새 비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (newPw !== newPwConfirm) {
      Alert.alert('입력 오류', '새 비밀번호가 일치하지 않습니다.');
      return;
    }
    setPwChanging(true);
    try {
      await withAuth((token) => editUser(token, { new_password: newPw }));
      setNewPw('');
      setNewPwConfirm('');
      Alert.alert('변경 완료', '비밀번호가 변경되었습니다.');
    } catch (e: any) {
      Alert.alert('오류', e?.message ?? '비밀번호 변경에 실패했습니다.');
    } finally {
      setPwChanging(false);
    }
  };

  const avatarUri = editMode ? editPhotoUri : profile?.profile_image;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>회원 정보</ThemedText>
        {profile && !loading ? (
          editMode ? (
            <View style={styles.headerActions}>
              <TouchableOpacity onPress={cancelEditMode} style={styles.headerBtn} hitSlop={8}>
                <ThemedText style={styles.headerBtnTextCancel}>취소</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={handleSaveProfile}
                style={styles.headerBtn}
                hitSlop={8}
                disabled={saving}>
                <ThemedText style={styles.headerBtnTextSave}>
                  {saving ? '저장 중' : '저장'}
                </ThemedText>
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity onPress={enterEditMode} style={styles.headerBtn} hitSlop={8}>
              <ThemedText style={styles.headerBtnTextEdit}>편집</ThemedText>
            </TouchableOpacity>
          )
        ) : (
          <View style={styles.headerRight} />
        )}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={ACCENT_GREEN} />
          <ThemedText style={{ marginTop: 10, color: SUB }}>불러오는 중...</ThemedText>
        </View>
      ) : !authEmail ? (
        <View style={styles.center}>
          <MaterialIcons name="person-off" size={48} color={SUB} />
          <ThemedText style={styles.centerTitle}>로그인이 필요합니다</ThemedText>
          <ThemedText style={styles.centerSub}>로그인 후 회원 정보를 확인할 수 있어요.</ThemedText>
        </View>
      ) : authEmail === 'google' ? (
        <View style={styles.center}>
          <MaterialIcons name="info-outline" size={48} color={SUB} />
          <ThemedText style={styles.centerTitle}>구글 로그인 계정</ThemedText>
          <ThemedText style={styles.centerSub}>
            현재는 구글 계정의 프로필 정보를 로컬에 저장하지 않아서{'\n'}
            회원정보 화면에 표시할 데이터가 없습니다.
          </ThemedText>
        </View>
      ) : !profile ? (
        <View style={styles.center}>
          <MaterialIcons name="error-outline" size={48} color={SUB} />
          <ThemedText style={styles.centerTitle}>프로필을 찾을 수 없습니다</ThemedText>
          <ThemedText style={styles.centerSub}>
            가입 정보가 로컬 저장소에 없거나 삭제되었을 수 있어요.
          </ThemedText>
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
          showsVerticalScrollIndicator={false}>
          {/* Profile card */}
          <View style={styles.profileCard}>
            <View style={styles.profileTop}>
              <TouchableOpacity
                onPress={editMode ? pickPhoto : undefined}
                activeOpacity={editMode ? 0.7 : 1}
                style={styles.avatarWrap}>
                {avatarUri ? (
                  <Image source={{ uri: avatarUri }} style={styles.avatar} contentFit="cover" />
                ) : (
                  <View style={styles.avatarFallback}>
                    <MaterialIcons name="person" size={34} color={SUB} />
                  </View>
                )}
                {editMode && (
                  <View style={styles.avatarEditBadge}>
                    <MaterialIcons name="camera-alt" size={14} color="#fff" />
                  </View>
                )}
              </TouchableOpacity>

              <View style={{ flex: 1 }}>
                <ThemedText style={styles.nameText}>{profile.name ?? '-'}</ThemedText>
                <ThemedText style={styles.emailText}>{profile.email}</ThemedText>
                {/* 편집 모드 + 기존 S3 사진 있을 때만 삭제 버튼 */}
                {editMode && !!profile.profile_image && editPhotoUri === profile.profile_image && (
                  <TouchableOpacity
                    style={styles.photoDeleteBtn}
                    onPress={handleDeletePhoto}
                    disabled={deleting || saving}
                    hitSlop={8}>
                    {deleting ? (
                      <ActivityIndicator size="small" color={ERROR_RED} />
                    ) : (
                      <ThemedText style={styles.photoDeleteText}>사진 삭제</ThemedText>
                    )}
                  </TouchableOpacity>
                )}
              </View>
            </View>

            <View style={styles.divider} />

            <Row label="별명" value={profile.nickname} />
            <Row label="생년월일" value={profile.birth} />

            {/* 소속 */}
            <View style={styles.row}>
              <ThemedText style={styles.rowLabel}>소속</ThemedText>
              {editMode ? (
                <View style={styles.affiliationRow}>
                  {AFFILIATION_OPTIONS.map((opt) => (
                    <TouchableOpacity
                      key={opt.value}
                      style={[
                        styles.affiliationChip,
                        editAffiliation === opt.value && styles.affiliationChipSelected,
                      ]}
                      onPress={() =>
                        setEditAffiliation(editAffiliation === opt.value ? undefined : opt.value)
                      }>
                      <ThemedText
                        style={[
                          styles.affiliationLabel,
                          editAffiliation === opt.value && styles.affiliationLabelSelected,
                        ]}>
                        {opt.label}
                      </ThemedText>
                    </TouchableOpacity>
                  ))}
                </View>
              ) : (
                <ThemedText style={styles.rowValue}>{profile.affiliation ?? '-'}</ThemedText>
              )}
            </View>
          </View>

          {/* 비밀번호 변경 (편집 모드에서만) */}
          {editMode && (
            <View style={styles.pwCard}>
              <ThemedText style={styles.pwCardTitle}>비밀번호 변경</ThemedText>

              <ThemedText style={styles.pwLabel}>새 비밀번호 (8자 이상)</ThemedText>
              <TextInput
                style={styles.pwInput}
                placeholder="8자 이상"
                placeholderTextColor={SUB}
                value={newPw}
                onChangeText={setNewPw}
                secureTextEntry
                editable={!pwChanging}
              />

              <ThemedText style={[styles.pwLabel, { marginTop: 12 }]}>새 비밀번호 확인</ThemedText>
              <TextInput
                style={styles.pwInput}
                placeholder="새 비밀번호 다시 입력"
                placeholderTextColor={SUB}
                value={newPwConfirm}
                onChangeText={setNewPwConfirm}
                secureTextEntry
                editable={!pwChanging}
              />

              <TouchableOpacity
                style={[styles.pwButton, pwChanging && styles.pwButtonDisabled]}
                onPress={handleChangePassword}
                disabled={pwChanging}
                activeOpacity={0.8}>
                <ThemedText style={styles.pwButtonText}>
                  {pwChanging ? '변경 중...' : '비밀번호 변경'}
                </ThemedText>
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 14,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: BORDER,
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: TEXT },
  headerRight: { width: 48 },
  headerActions: { flexDirection: 'row', gap: 8 },
  headerBtn: { paddingHorizontal: 8, paddingVertical: 4 },
  headerBtnTextEdit: { fontSize: 15, fontWeight: '700', color: ACCENT_GREEN },
  headerBtnTextSave: { fontSize: 15, fontWeight: '700', color: ACCENT_GREEN },
  headerBtnTextCancel: { fontSize: 15, fontWeight: '600', color: SUB },

  scroll: { flex: 1, padding: 18 },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  centerTitle: { marginTop: 10, fontSize: 16, fontWeight: '800', color: TEXT, textAlign: 'center' },
  centerSub: { marginTop: 8, fontSize: 13, color: SUB, textAlign: 'center', lineHeight: 18 },

  profileCard: {
    backgroundColor: CARD_BG,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: BORDER,
  },

  profileTop: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatarWrap: { position: 'relative' },
  avatar: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#eee' },
  avatarFallback: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#F0F0F0',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: BORDER,
  },
  avatarEditBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: ACCENT_GREEN,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#fff',
  },

  nameText: { fontSize: 18, fontWeight: '900', color: TEXT },
  emailText: { marginTop: 4, fontSize: 13, color: SUB },

  divider: { height: 1, backgroundColor: BORDER, marginVertical: 14 },

  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  rowLabel: { width: 90, fontSize: 14, color: SUB, fontWeight: '700' },
  rowValue: { flex: 1, fontSize: 14, color: TEXT, fontWeight: '800' },

  affiliationRow: { flexDirection: 'row', gap: 8, flex: 1, flexWrap: 'wrap' },
  affiliationChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: '#F0F0F0',
  },
  affiliationChipSelected: { backgroundColor: ACCENT_GREEN },
  affiliationLabel: { fontSize: 13, fontWeight: '600', color: SUB },
  affiliationLabelSelected: { color: '#fff' },

  // 비밀번호 변경 카드
  pwCard: {
    backgroundColor: CARD_BG,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: BORDER,
    marginTop: 16,
  },
  pwCardTitle: { fontSize: 15, fontWeight: '800', color: TEXT, marginBottom: 16 },
  pwLabel: { fontSize: 13, fontWeight: '600', color: SUB, marginBottom: 6 },
  pwInput: {
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: TEXT,
    borderWidth: 1,
    borderColor: BORDER,
  },
  pwButton: {
    backgroundColor: ACCENT_GREEN,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  pwButtonDisabled: { opacity: 0.6 },
  pwButtonText: { fontSize: 15, fontWeight: '700', color: '#fff' },

  photoDeleteBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 },
  photoDeleteText: { fontSize: 12, fontWeight: '600', color: ERROR_RED },
});
