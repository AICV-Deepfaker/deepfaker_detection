import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { getAuth, getProfileByEmail, type StoredUser } from '@/lib/auth-storage';

const ACCENT_GREEN = '#00CF90';
const TEXT = '#111';
const SUB = '#687076';
const CARD_BG = '#fff';
const BORDER = 'rgba(0,0,0,0.06)';

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
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  const [profile, setProfile] = useState<StoredUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const auth = await getAuth();
      const email = auth?.email ?? null;
      setAuthEmail(email);

      if (!email) {
        setProfile(null);
        return;
      }

      // ✅ 구글 로그인은 로컬 users에 저장된 프로필이 없을 수 있음
      if (email === 'google') {
        setProfile(null);
        return;
      }

      const p = await getProfileByEmail(email);
      setProfile(p);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>회원 정보</ThemedText>
        <View style={styles.headerRight} />
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
          showsVerticalScrollIndicator={false}
        >
          {/* Profile card */}
          <View style={styles.profileCard}>
            <View style={styles.profileTop}>
              {profile.profilePhotoUri ? (
                <Image source={{ uri: profile.profilePhotoUri }} style={styles.avatar} contentFit="cover" />
              ) : (
                <View style={styles.avatarFallback}>
                  <MaterialIcons name="person" size={34} color={SUB} />
                </View>
              )}

              <View style={{ flex: 1 }}>
                <ThemedText style={styles.nameText}>{profile.name ?? '-'}</ThemedText>
                <ThemedText style={styles.emailText}>{profile.email}</ThemedText>
              </View>
            </View>

            <View style={styles.divider} />

            <Row label="별명" value={profile.nickname} />
            <Row label="생년월일" value={profile.birthdate} />
            <Row label="소속" value={profile.affiliation ?? '-'} />
          </View>
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
  headerRight: { width: 32 },

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

  nameText: { fontSize: 18, fontWeight: '900', color: TEXT },
  emailText: { marginTop: 4, fontSize: 13, color: SUB },

  divider: { height: 1, backgroundColor: BORDER, marginVertical: 14 },

  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  rowLabel: { width: 90, fontSize: 14, color: SUB, fontWeight: '700' },
  rowValue: { flex: 1, fontSize: 14, color: TEXT, fontWeight: '800' },
});