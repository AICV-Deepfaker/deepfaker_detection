import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import { useCallback } from 'react';
import { Alert, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { clearAuth } from '@/lib/auth-storage';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

function RowItem({
  icon,
  label,
  onPress,
  showChevron = true,
}: {
  icon: React.ComponentProps<typeof MaterialIcons>['name'];
  label: string;
  onPress: () => void;
  showChevron?: boolean;
}) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress} activeOpacity={0.7}>
      <MaterialIcons name={icon} size={22} color={TEXT_COLOR} />
      <ThemedText style={styles.rowLabel}>{label}</ThemedText>
      {showChevron && <MaterialIcons name="chevron-right" size={22} color={SECONDARY_TEXT_COLOR} />}
    </TouchableOpacity>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <ThemedText style={styles.sectionTitle}>{title}</ThemedText>;
}

export default function MypageScreen() {
  const insets = useSafeAreaInsets();
  const { totalPoints } = useAnalysis();

  const handleLogout = useCallback(() => {
    Alert.alert('로그아웃', '로그아웃 하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '로그아웃',
        style: 'destructive',
        onPress: () => {
          clearAuth();
          router.replace('/login');
        },
      },
    ]);
  }, []);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <ThemedText style={styles.headerTitle}>My page</ThemedText>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 120 }]}
        showsVerticalScrollIndicator={false}>
        {/* 프로필 - 회원 정보 */}
        <SectionTitle title="프로필" />
        <View style={styles.card}>
          <RowItem
            icon="person-outline"
            label="회원 정보"
            onPress={() => router.push('/(tabs)/member-info')}
          />
        </View>

        {/* 포인트 내역 */}
        <SectionTitle title="포인트" />
        <View style={styles.card}>
          <TouchableOpacity style={styles.row} activeOpacity={0.7} onPress={() => router.push('/fraud-report')}>
            <MaterialIcons name="account-balance-wallet" size={22} color={TEXT_COLOR} />
            <ThemedText style={styles.rowLabel}>포인트 내역</ThemedText>
            <ThemedText style={styles.pointBadge}>{totalPoints.toLocaleString()}P</ThemedText>
            <MaterialIcons name="chevron-right" size={22} color={SECONDARY_TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* 문의하기 */}
        <SectionTitle title="고객지원" />
        <View style={styles.card}>
          <RowItem
            icon="chat-bubble-outline"
            label="문의하기"
            onPress={() => router.push('/inquiry')}
          />
        </View>

        {/* 환경 설정 */}
        <SectionTitle title="환경 설정" />
        <View style={styles.card}>
          <RowItem
            icon="description"
            label="서비스 이용약관"
            onPress={() => Alert.alert('서비스 이용약관', '이용약관 화면 연동 예정')}
          />
          <View style={styles.divider} />
          <RowItem
            icon="policy"
            label="개인정보 처리방침"
            onPress={() => Alert.alert('개인정보 처리방침', '개인정보 처리방침 화면 연동 예정')}
          />
          <View style={styles.divider} />
          <RowItem
            icon="language"
            label="언어"
            onPress={() => Alert.alert('언어', '언어 설정 연동 예정')}
          />
        </View>

        {/* 로그아웃 */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout} activeOpacity={0.8}>
          <MaterialIcons name="logout" size={22} color="#E53935" />
          <ThemedText style={styles.logoutText}>로그아웃</ThemedText>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 18,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingTop: 24,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 10,
    marginLeft: 4,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 24,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    gap: 12,
  },
  rowLabel: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: TEXT_COLOR,
  },
  pointBadge: {
    fontSize: 15,
    fontWeight: '700',
    color: ACCENT_GREEN,
  },
  divider: {
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.06)',
    marginLeft: 50,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    marginTop: 8,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#E53935',
  },
});
