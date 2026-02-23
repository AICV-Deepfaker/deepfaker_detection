import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import {
  useAnalysis,
  HistoryItem,
  getBadgeForPoints,
  POINTS_PER_REPORT,
  GIFT_THRESHOLD,
} from '@/contexts/analysis-context';

import AsyncStorage from '@react-native-async-storage/async-storage';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function FraudReportScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ link?: string; historyId?: string }>();
  const { totalPoints, addPoints, incrementReportCount, getHistoryByLink } = useAnalysis();
  const { current: currentBadge, next: nextBadge } = getBadgeForPoints(totalPoints);

  const [link, setLink] = useState(params.link || '');
  const [showHistorySelect, setShowHistorySelect] = useState(false);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successPoints, setSuccessPoints] = useState(0);

  const markReportedIfFromHistory = useCallback(async () => {
    const historyId = params.historyId;
    if (!historyId) return; // 상세화면에서 온게 아니면 저장 안 함
    await AsyncStorage.setItem(`reported:${historyId}`, '1');
  }, [params.historyId]);

  const handleSubmit = useCallback(async () => {
    const trimmedLink = link.trim();
    if (!trimmedLink) {
      Alert.alert('입력 필요', '영상 링크를 입력해주세요.');
      return;
    }

    const existingHistory = getHistoryByLink(trimmedLink);
    if (existingHistory.length > 0) {
      setHistoryItems(existingHistory);
      setShowHistorySelect(true);
      return;
    }
    await markReportedIfFromHistory();

    addPoints(POINTS_PER_REPORT);
    incrementReportCount();
    setSuccessPoints(POINTS_PER_REPORT);
    setShowSuccessModal(true);
  }, [link, getHistoryByLink, addPoints, incrementReportCount]);

  const handleSelectHistory = useCallback(async (item: HistoryItem) => {
    setShowHistorySelect(false);
    await markReportedIfFromHistory();
    addPoints(POINTS_PER_REPORT);
    incrementReportCount();
    setSuccessPoints(POINTS_PER_REPORT);
    setShowSuccessModal(true);
  }, [markReportedIfFromHistory, addPoints, incrementReportCount]);

  const handleSuccessClose = () => {
    setShowSuccessModal(false);
    router.back();
  };

  const handleCancel = () => {
    router.back();
  };

  const progressToNext =
    nextBadge && nextBadge.minPoints > totalPoints
      ? Math.min(100, ((totalPoints - currentBadge.minPoints) / (nextBadge.minPoints - currentBadge.minPoints)) * 100)
      : 100;
  const nextPointsNeeded = nextBadge ? nextBadge.minPoints - totalPoints : 0;


  const myUserId = 'me'; // TODO: 나중에 auth에서 가져오기
  const myNickname = '지윤캥'; // TODO: 나중에 auth에서 가져오기

  type RankUser = { userId: string; name: string; points: number };

  const BASE_RANKING: RankUser[] = [
    { userId: 'u1', name: '민진', points: 12400 },
    { userId: 'u2', name: '도현', points: 10250 },
    { userId: 'u3', name: '예슬', points: 8200 },
    { userId: 'u4', name: '재민', points: 6000 },
    { userId: 'u5', name: '강혁', points: 4500 },
    { userId: 'u6', name: '동하', points: 2200 },
    { userId: 'u7', name: '우일', points: 1000 },
    { userId: 'u8', name: '허건', points: 300 },
    { userId: 'u9', name: '어진', points: 200 },
    { userId: 'u10', name: '민성', points: 100 },
  ];

  // ✅ 내 유저를 totalPoints로 덮어써서 합치기 (중복 방지)
  const rankingWithMe: RankUser[] = [
    ...BASE_RANKING.filter((u) => u.userId !== myUserId),
    { userId: myUserId, name: myNickname, points: 5000 }, //숫자말고 totalPoints
  ];

  // ✅ 점수 내림차순, 동점이면 이름 오름차순
  const sortedRanking = [...rankingWithMe].sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    return a.name.localeCompare(b.name);
  });

  const myRankIndex = sortedRanking.findIndex((u) => u.userId === myUserId);
  const myRank = myRankIndex >= 0 ? myRankIndex + 1 : null;

  // ✅ TOP10만 뽑기 (내 점수 반영된 결과)
  const top10 = sortedRanking.slice(0, 10);

  // (선택) TOP3 카드 안전 접근용
  const first = top10[0];
  const second = top10[1];
  const third = top10[2];

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}
    >
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <ThemedText style={styles.headerTitle}>포인트 내역</ThemedText>
          <TouchableOpacity onPress={handleCancel} style={styles.closeButton} hitSlop={12}>
            <MaterialIcons name="close" size={24} color={TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* Reward */}
        <View style={styles.rewardSection}>
          <Image
            source={require('@/assets/images/coin.png')}
            style={styles.coinImage}
            contentFit="contain"
          />
          <View style={styles.rewardInfo}>
            <ThemedText style={styles.rewardLabel}>보유 포인트</ThemedText>
            <ThemedText style={styles.rewardAmount}>{totalPoints.toLocaleString()} P</ThemedText>
          </View>
        </View>

        {/* Badge */}
        <View style={styles.badgeSection}>
          <ThemedText style={styles.badgeSectionTitle}>디지털 뱃지 & 등급</ThemedText>

          <View style={styles.currentBadgeCard}>
            <View style={styles.badgeIconWrap}>
              <ThemedText style={styles.badgeEmoji}>{currentBadge.icon}</ThemedText>
            </View>
            <View style={styles.badgeContent}>
              <ThemedText style={styles.badgeName}>{currentBadge.name}</ThemedText>
              <ThemedText style={styles.badgeDesc}>{currentBadge.desc}</ThemedText>
            </View>
          </View>

          {nextBadge && nextPointsNeeded > 0 && (
            <View style={styles.nextTierRow}>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${progressToNext}%` }]} />
              </View>
              <ThemedText style={styles.nextTierText}>
                다음 등급 <ThemedText style={styles.nextTierName}>{nextBadge.name}</ThemedText>까지{' '}
                {nextPointsNeeded.toLocaleString()}P
              </ThemedText>
            </View>
          )}

          <View style={styles.rewardInfoList}>
            <ThemedText style={styles.rewardInfoItem}>
              🎁 {GIFT_THRESHOLD.toLocaleString()}P 달성 시 스타벅스 아메리카노 기프티콘
            </ThemedText>
            <ThemedText style={styles.rewardInfoItem}>🏅 100,000P 달성 시 경찰청장상 수상급</ThemedText>
          </View>

          {/* ✅ Ranking Section (badgeSection 안쪽에서 끝내고, badgeSection 닫기!) */}
          <View style={styles.rankingSection}>
            <ThemedText style={styles.rankingTitle}>전체 포인트 랭킹</ThemedText>
            <ThemedText style={styles.rankingSubtitle}>상위 신고 기여자 TOP 10</ThemedText>

            {/* Top 3 */}
            <View style={styles.podiumRow}>
              <View style={[styles.podiumCard, styles.podiumSilver]}>
                <View style={styles.podiumCircle}>
                  <ThemedText style={styles.podiumRank}>2</ThemedText>
                </View>
                <ThemedText style={styles.podiumName} numberOfLines={1}>
                  {second?.name ?? '-'}
                </ThemedText>
                <ThemedText style={styles.podiumPoints}>
                  {(second?.points ?? 0).toLocaleString()}P
                </ThemedText>
              </View>

              <View style={[styles.podiumCard, styles.podiumGold]}>
                <View style={[styles.podiumCircle, styles.podiumCircleGold]}>
                  <ThemedText style={styles.podiumRank}>1</ThemedText>
                </View>
                <ThemedText style={[styles.podiumName, { fontSize: 16 }]} numberOfLines={1}>
                  {first?.name ?? '-'}
                </ThemedText>
                <ThemedText style={[styles.podiumPoints, { fontSize: 15 }]}>
                  {(first?.points ?? 0).toLocaleString()}P
                </ThemedText>
                <View style={styles.crownTag}>
                  <ThemedText style={styles.crownTagText}>TOP</ThemedText>
                </View>
              </View>

              <View style={[styles.podiumCard, styles.podiumBronze]}>
                <View style={styles.podiumCircle}>
                  <ThemedText style={styles.podiumRank}>3</ThemedText>
                </View>
                <ThemedText style={styles.podiumName} numberOfLines={1}>
                  {third?.name ?? '-'}
                </ThemedText>
                <ThemedText style={styles.podiumPoints}>
                  {(third?.points ?? 0).toLocaleString()}P
                </ThemedText>
              </View>
            </View>

            {/* 4~10 */}
            <View style={styles.rankingCard}>
              {top10.slice(3, 10).map((u, idx) => {
                const rank = idx + 4;
                const isMe = u.userId === myUserId;

                return (
                  <View key={`${u.userId}-${rank}`} style={[styles.rankRow, isMe && styles.rankRowMe]}>
                    <View style={styles.rankLeft}>
                      <View style={[styles.rankBadge, isMe && styles.rankBadgeMe]}>
                        <ThemedText style={[styles.rankBadgeText, isMe && styles.rankBadgeTextMe]}>
                          {rank}
                        </ThemedText>
                      </View>
                      <ThemedText style={[styles.rankName, isMe && styles.rankNameMe]} numberOfLines={1}>
                        {u.name}
                      </ThemedText>
                    </View>
                    <ThemedText style={[styles.rankPoints, isMe && styles.rankPointsMe]}>
                      {u.points.toLocaleString()}P
                    </ThemedText>
                  </View>
                );
              })}

              <View style={styles.myRankRow}>
                <ThemedText style={styles.myRankText}>
                  내 순위: <ThemedText style={styles.myRankEm}>{myRank ? `${myRank}위` : '-'}</ThemedText>{' '}
                  ({totalPoints.toLocaleString()}P)
                </ThemedText>
              </View>
            </View>
          </View>
        </View>

        {/* ✅ ScrollView 내부는 여기서 끝 */}
      </ScrollView>

      {/* ✅ ScrollView 밖: 모달/오버레이는 여기 */}
      {showHistorySelect && historyItems.length > 0 && (
        <View style={styles.historyOverlay}>
          <View style={styles.historySheet}>
            <ThemedText style={styles.historyTitle}>이전 분석 결과 선택</ThemedText>
            <ThemedText style={styles.historySubtitle}>
              이 링크는 이미 분석된 기록이 있습니다. 제출할 결과를 선택하세요.
            </ThemedText>

            {historyItems.map((item) => (
              <TouchableOpacity
                key={item.id}
                style={styles.historyItem}
                activeOpacity={0.8}
                onPress={() => handleSelectHistory(item)}
              >
                <ThemedText style={styles.historyItemResult} numberOfLines={2}>
                  {item.result}
                </ThemedText>
                <ThemedText style={styles.historyItemDate}>
                  {new Date(item.date).toLocaleDateString('ko-KR')}
                </ThemedText>
              </TouchableOpacity>
            ))}

            <TouchableOpacity style={styles.historyCancel} onPress={() => setShowHistorySelect(false)}>
              <ThemedText style={styles.historyCancelText}>취소</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      )}

      <Modal visible={showSuccessModal} transparent animationType="fade">
        <View style={styles.successOverlay}>
          <View style={styles.successCard}>
            <View style={styles.successIconWrap}>
              <ThemedText style={styles.successEmoji}>🎉</ThemedText>
            </View>
            <ThemedText style={styles.successTitle}>신고 완료</ThemedText>
            <ThemedText style={styles.successPoints}>
              +{successPoints.toLocaleString()} 포인트가 지급되었습니다!
            </ThemedText>
            <ThemedText style={styles.successSubtext}>
              {GIFT_THRESHOLD.toLocaleString()}포인트를 모으면 스타벅스 아메리카노 기프티콘을 제공합니다.
            </ThemedText>

            <TouchableOpacity style={styles.successButton} onPress={handleSuccessClose} activeOpacity={0.8}>
              <ThemedText style={styles.successButtonText}>확인</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },

  // --------------------
  // Header
  // --------------------
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 28, // ✅ 약간 줄여서 밸런스
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800', // ✅ 조금 더 단단하게
    color: TEXT_COLOR,
    letterSpacing: -0.2,
  },
  closeButton: { padding: 4 },

  // --------------------
  // Reward card
  // --------------------
  rewardSection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 18, // ✅ 좀 더 고급
    padding: 20,
    marginBottom: 18,
    gap: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',

    // ✅ subtle shadow
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  coinImage: { width: 60, height: 60 },
  rewardInfo: { flex: 1 },
  rewardLabel: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 4,
  },
  rewardAmount: {
    fontSize: 22,
    fontWeight: '800',
    color: ACCENT_GREEN_DARK,
    letterSpacing: -0.2,
  },

  // --------------------
  // Badge section
  // --------------------
  badgeSection: {
    marginBottom: 24,
  },
  badgeSectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 12,
    letterSpacing: -0.15,
  },
  currentBadgeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    gap: 14,

    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },
  badgeIconWrap: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(0, 207, 144, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeEmoji: { fontSize: 28 },
  badgeContent: { flex: 1 },
  badgeName: {
    fontSize: 17,
    fontWeight: '800',
    color: TEXT_COLOR,
    marginBottom: 4,
    letterSpacing: -0.2,
  },
  badgeDesc: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 18,
  },

  // --------------------
  // Progress
  // --------------------
  nextTierRow: { marginBottom: 14 },
  progressBarBg: {
    height: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.08)',
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: ACCENT_GREEN,
  },
  nextTierText: { fontSize: 13, color: SECONDARY_TEXT_COLOR },
  nextTierName: { fontWeight: '800', color: ACCENT_GREEN_DARK },

  rewardInfoList: { gap: 6 },
  rewardInfoItem: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 20,
  },

  // --------------------
  // History modal
  // --------------------
  historyOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
    zIndex: 10,
  },
  historySheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    paddingBottom: 40,
  },
  historyTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: TEXT_COLOR,
    marginBottom: 8,
    letterSpacing: -0.2,
  },
  historySubtitle: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 20,
    lineHeight: 20,
  },
  historyItem: {
    backgroundColor: '#F5F5F5',
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: ACCENT_GREEN,
  },
  historyItemResult: {
    fontSize: 14,
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  historyItemDate: { fontSize: 12, color: SECONDARY_TEXT_COLOR },
  historyCancel: { marginTop: 12, paddingVertical: 14, alignItems: 'center' },
  historyCancelText: { fontSize: 16, color: SECONDARY_TEXT_COLOR },

  // --------------------
  // Success modal
  // --------------------
  successOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  successCard: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
  },
  successIconWrap: { marginBottom: 16 },
  successEmoji: { fontSize: 56 },
  successTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: TEXT_COLOR,
    marginBottom: 12,
  },
  successPoints: {
    fontSize: 18,
    fontWeight: '800',
    color: ACCENT_GREEN_DARK,
    marginBottom: 8,
  },
  successSubtext: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 20,
  },
  successBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(0, 207, 144, 0.1)',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  successBadgeEmoji: { fontSize: 24 },
  successBadgeName: {
    fontSize: 16,
    fontWeight: '800',
    color: ACCENT_GREEN_DARK,
  },
  successButton: {
    backgroundColor: ACCENT_GREEN,
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 14,
    width: '100%',
    alignItems: 'center',
  },
  successButtonText: { fontSize: 16, fontWeight: '700', color: '#fff' },

  // --------------------
  // Ranking section
  // --------------------
  rankingSection: { marginTop: 28, marginBottom: 24 },
  rankingTitle: {
    fontSize: 20, // ✅ 더 커짐
    fontWeight: '900',
    color: TEXT_COLOR,
    marginBottom: 6,
    letterSpacing: -0.25,
  },
  rankingSubtitle: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 14,
  },

  podiumRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  podiumCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 18,
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  podiumGold: {
    transform: [{ translateY: -6 }],
    borderColor: 'rgba(0, 207, 144, 0.45)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 14,
    elevation: 3,
  },
  podiumSilver: { backgroundColor: '#FFFFFF' },
  podiumBronze: { backgroundColor: '#FFFFFF' },

  podiumCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.06)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  podiumCircleGold: { backgroundColor: 'rgba(0, 207, 144, 0.14)' },
  podiumRank: { fontSize: 16, fontWeight: '900', color: TEXT_COLOR },

  podiumName: {
    fontSize: 14,
    fontWeight: '900',
    color: TEXT_COLOR,
    marginBottom: 4,
  },
  podiumPoints: {
    fontSize: 13,
    fontWeight: '900',
    color: ACCENT_GREEN_DARK,
  },

  crownTag: {
    marginTop: 10,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: ACCENT_GREEN,
  },
  crownTagText: { color: '#fff', fontSize: 12, fontWeight: '900' },

  rankingCard: {
    backgroundColor: '#fff',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    overflow: 'hidden',
  },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.04)',
  },
  rankLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  rankBadge: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: 'rgba(0,0,0,0.06)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankBadgeText: { fontWeight: '900', color: TEXT_COLOR },
  rankName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '800',
    color: TEXT_COLOR,
  },
  rankPoints: {
    fontSize: 15,
    fontWeight: '900',
    color: SECONDARY_TEXT_COLOR,
  },

  // ✅ 내가 TOP10에 들어왔을 때 강조 (너가 JSX에서 이미 쓰고 있음)
  rankRowMe: {
    backgroundColor: 'rgba(0, 207, 144, 0.08)',
  },
  rankBadgeMe: {
    backgroundColor: 'rgba(0, 207, 144, 0.18)',
  },
  rankBadgeTextMe: {
    color: ACCENT_GREEN_DARK,
  },
  rankNameMe: {
    color: TEXT_COLOR,
    fontWeight: '900',
  },
  rankPointsMe: {
    color: ACCENT_GREEN_DARK,
  },

  myRankRow: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(0, 207, 144, 0.10)',
  },
  myRankText: {
    fontSize: 14,
    fontWeight: '800',
    color: TEXT_COLOR,
    textAlign: 'center',
  },
  myRankEm: { color: ACCENT_GREEN_DARK, fontWeight: '900' },
});