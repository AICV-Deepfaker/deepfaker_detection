import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import React, { useCallback, useMemo, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { clearAuth, getAuth } from '@/lib/auth-storage';
import { logout as logoutApi, withdraw as withdrawApi } from '@/lib/account-api';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';
const DANGER = '#E53935';

import { useFocusEffect } from 'expo-router';
import { getMe } from '@/lib/api';


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

type ConfirmVariant = 'logout' | 'withdraw';

function ConfirmModal({
  visible,
  variant,
  onClose,
  onConfirm,
}: {
  visible: boolean;
  variant: ConfirmVariant;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const content = useMemo(() => {
    if (variant === 'withdraw') {
      return {
        icon: 'warning-amber',
        iconBg: 'rgba(229,57,53,0.10)',
        iconColor: DANGER,
        title: '정말 탈퇴하시겠어요?',
        desc: '탈퇴 시 계정 정보와 이용 기록이 모두 삭제되며,\n복구가 불가능해요. 신중히 생각하신 후\n진행하시려면 아래 버튼을 눌러주세요.',
        confirmText: '탈퇴하기',
        confirmBg: DANGER,
      };
    }
    return {
      icon: 'logout',
      iconBg: 'rgba(0,207,144,0.12)',
      iconColor: ACCENT_GREEN,
      title: '로그아웃 하시겠어요?',
      desc: '로그인 상태가 해제됩니다.\n다시 이용하려면 로그인해야 해요.',
      confirmText: '로그아웃',
      confirmBg: ACCENT_GREEN,
    };
  }, [variant]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        {/* 바깥 눌러 닫기 */}
        <Pressable style={styles.modalBackdrop} onPress={onClose} />

        <View style={styles.modalCard}>
          <View style={[styles.modalIconWrap, { backgroundColor: content.iconBg }]}>
            <MaterialIcons name={content.icon as any} size={26} color={content.iconColor} />
          </View>

          <ThemedText style={styles.modalTitle}>{content.title}</ThemedText>
          <ThemedText style={styles.modalDesc}>{content.desc}</ThemedText>

          <View style={styles.modalButtonRow}>
            <TouchableOpacity style={styles.modalBtnGhost} onPress={onClose} activeOpacity={0.85}>
              <ThemedText style={styles.modalBtnGhostText}>취소</ThemedText>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.modalBtnPrimary, { backgroundColor: content.confirmBg }]}
              onPress={onConfirm}
              activeOpacity={0.85}
            >
              <ThemedText style={styles.modalBtnPrimaryText}>{content.confirmText}</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

export default function MypageScreen() {
  const insets = useSafeAreaInsets();
  const { points } = useAnalysis();
  const { setPointsFromServer } = useAnalysis();

  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          const me = await getMe();
          setPointsFromServer({ activePoints: me.active_points, totalPoints: me.total_points });
        } catch {
          // 로그인 전 등 예외 상황이면 조용히 무시하거나 안내
        }
      })();
    }, [setPointsFromServer])
  );

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmVariant, setConfirmVariant] = useState<ConfirmVariant>('logout');

  const openLogout = useCallback(() => {
    setConfirmVariant('logout');
    setConfirmOpen(true);
  }, []);

  const openWithdraw = useCallback(() => {
    setConfirmVariant('withdraw');
    setConfirmOpen(true);
  }, []);

  const closeConfirm = useCallback(() => setConfirmOpen(false), []);

  const doLogout = useCallback(async () => {
    setConfirmOpen(false);

    const auth = await getAuth();
    if (!auth) return;

    try {
      await logoutApi(auth.refreshToken);
    } catch (e) {
      console.log('서버 로그아웃 실패, 로컬만 진행');
    }

    await clearAuth();
    router.replace('/login');
  }, []);

  const doWithdraw = useCallback(async () => {
    setConfirmOpen(false);

    const auth = await getAuth();
    if (!auth) return;

    try {
      await withdrawApi(auth.accessToken);
    } catch (e) {
      alert('탈퇴 실패');
      return;
    }

    await clearAuth();
    router.replace('/login');
  }, []);

  const handleConfirm = useCallback(() => {
    if (confirmVariant === 'withdraw') doWithdraw();
    else doLogout();
  }, [confirmVariant, doWithdraw, doLogout]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <ThemedText style={styles.headerTitle}>My page</ThemedText>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 120 }]}
        showsVerticalScrollIndicator={false}
      >
        {/* 프로필 */}
        <SectionTitle title="프로필" />
        <View style={styles.card}>
          <RowItem icon="person-outline" label="회원 정보" onPress={() => router.push('/(tabs)/member-info')} />
        </View>

        {/* 포인트 */}
        <SectionTitle title="포인트" />
        <View style={styles.card}>
          <TouchableOpacity style={styles.row} activeOpacity={0.7} onPress={() => router.push('/fraud-report')}>
            <MaterialIcons name="account-balance-wallet" size={22} color={TEXT_COLOR} />
            <ThemedText style={styles.rowLabel}>포인트 내역</ThemedText>
            <ThemedText style={styles.pointBadge}>
              {(points?.activePoints ?? 0).toLocaleString()}P
            </ThemedText>
            <MaterialIcons name="chevron-right" size={22} color={SECONDARY_TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* 고객지원 */}
        <SectionTitle title="고객지원" />
        <View style={styles.card}>
          <RowItem icon="chat-bubble-outline" label="문의하기" onPress={() => router.push('/inquiry')} />
        </View>

        {/* 환경 설정 */}
        <SectionTitle title="환경 설정" />
        <View style={styles.card}>
          <RowItem
            icon="description"
            label="서비스 이용약관"
            onPress={() => router.push('/terms-of-service')}
          />
          <View style={styles.divider} />
          <RowItem
            icon="policy"
            label="개인정보 처리방침"
            onPress={() => router.push('/privacy-policy')}
          />
          <View style={styles.divider} />
          <RowItem
            icon="language"
            label="언어"
            onPress={() => {
              // TODO: 언어 화면
            }}
          />
        </View>

        {/* 로그아웃 / 탈퇴 */}
        <View style={styles.accountActions}>
          <TouchableOpacity style={styles.logoutButton} onPress={openLogout} activeOpacity={0.8}>
            <MaterialIcons name="logout" size={22} color={DANGER} />
            <ThemedText style={styles.logoutText}>로그아웃</ThemedText>
          </TouchableOpacity>

          {/* ✅ 탈퇴 추가 */}
          <TouchableOpacity style={styles.withdrawButton} onPress={openWithdraw} activeOpacity={0.8}>
            <MaterialIcons name="person-off" size={22} color={DANGER} />
            <ThemedText style={styles.withdrawText}>탈퇴하기</ThemedText>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* ✅ 커스텀 확인 모달 */}
      <ConfirmModal
        visible={confirmOpen}
        variant={confirmVariant}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },

  header: {
    paddingHorizontal: 20,
    paddingVertical: 18,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: TEXT_COLOR },

  scroll: { flex: 1 },
  scrollContent: { padding: 20, paddingTop: 24 },

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
  rowLabel: { flex: 1, fontSize: 16, fontWeight: '600', color: TEXT_COLOR },
  pointBadge: { fontSize: 15, fontWeight: '700', color: ACCENT_GREEN },

  divider: { height: 1, backgroundColor: 'rgba(0,0,0,0.06)', marginLeft: 50 },

  // -------------------------
  // 로그아웃/탈퇴
  // -------------------------
  accountActions: { marginTop: 8 },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
  },
  logoutText: { fontSize: 16, fontWeight: '700', color: DANGER },

  withdrawButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
  },
  withdrawText: { fontSize: 16, fontWeight: '700', color: 'rgba(229,57,53,0.95)' },

  // -------------------------
  // Modal (custom alert)
  // -------------------------
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.45)',
  },
  modalCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#fff',
    borderRadius: 22,
    padding: 22,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',

    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.10,
    shadowRadius: 18,
    elevation: 6,
  },
  modalIconWrap: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: TEXT_COLOR,
    marginBottom: 8,
    letterSpacing: -0.2,
  },
  modalDesc: {
    fontSize: 13,
    lineHeight: 19,
    color: SECONDARY_TEXT_COLOR,
    textAlign: 'center',
    marginBottom: 18,
  },
  modalButtonRow: {
    flexDirection: 'row',
    gap: 10,
    width: '100%',
  },
  modalBtnGhost: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 14,
    backgroundColor: '#F2F4F5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalBtnGhostText: {
    fontSize: 15,
    fontWeight: '800',
    color: TEXT_COLOR,
  },
  modalBtnPrimary: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalBtnPrimaryText: {
    fontSize: 15,
    fontWeight: '900',
    color: '#fff',
  },
});