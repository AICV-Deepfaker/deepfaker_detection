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

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function FraudReportScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ link?: string }>();
  const { totalPoints, addPoints, incrementReportCount, getHistoryByLink } = useAnalysis();
  const { current: currentBadge, next: nextBadge } = getBadgeForPoints(totalPoints);

  const [link, setLink] = useState(params.link || '');
  const [showHistorySelect, setShowHistorySelect] = useState(false);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successPoints, setSuccessPoints] = useState(0);

  const handleSubmit = useCallback(() => {
    const trimmedLink = link.trim();
    if (!trimmedLink) {
      Alert.alert('입력 필요', '영상 링크를 입력해주세요.');
      return;
    }

    const existingHistory = getHistoryByLink(trimmedLink);
    if (existingHistory.length > 0) {
      setHistoryItems(existingHistory);
      setShowHistorySelect(true);
    } else {
      addPoints(POINTS_PER_REPORT);
      incrementReportCount();
      setSuccessPoints(POINTS_PER_REPORT);
      setShowSuccessModal(true);
    }
  }, [link, getHistoryByLink, addPoints, incrementReportCount]);

  const handleSelectHistory = (item: HistoryItem) => {
    setShowHistorySelect(false);
    addPoints(POINTS_PER_REPORT);
    incrementReportCount();
    setSuccessPoints(POINTS_PER_REPORT);
    setShowSuccessModal(true);
  };

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

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <ThemedText style={styles.headerTitle}>금융사기 영상 신고</ThemedText>
          <TouchableOpacity onPress={handleCancel} style={styles.closeButton} hitSlop={12}>
            <MaterialIcons name="close" size={24} color={TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* Reward Section with coin.png */}
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

        {/* Badge & Rank Section */}
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
                {(nextBadge.minPoints - totalPoints).toLocaleString()}P
              </ThemedText>
            </View>
          )}
          <View style={styles.rewardInfoList}>
            <ThemedText style={styles.rewardInfoItem}>
              🎁 {GIFT_THRESHOLD.toLocaleString()}P 달성 시 스타벅스 아메리카노 기프티콘
            </ThemedText>
            <ThemedText style={styles.rewardInfoItem}>
              🏅 100,000P 달성 시 경찰청장상 수상급
            </ThemedText>
          </View>
        </View>

        {/* Link Input */}
        <View style={styles.inputSection}>
          <ThemedText style={styles.inputLabel}>영상 링크</ThemedText>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="영상 URL을 입력하거나 붙여넣어 주세요"
              placeholderTextColor={SECONDARY_TEXT_COLOR}
              value={link}
              onChangeText={setLink}
              multiline={false}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
          </View>
        </View>

        {/* History Selection Modal */}
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
                  onPress={() => handleSelectHistory(item)}>
                  <ThemedText style={styles.historyItemResult} numberOfLines={2}>
                    {item.result}
                  </ThemedText>
                  <ThemedText style={styles.historyItemDate}>
                    {new Date(item.date).toLocaleDateString('ko-KR')}
                  </ThemedText>
                </TouchableOpacity>
              ))}
              <TouchableOpacity
                style={styles.historyCancel}
                onPress={() => setShowHistorySelect(false)}>
                <ThemedText style={styles.historyCancelText}>취소</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Submit Button */}
        <TouchableOpacity style={styles.submitButton} activeOpacity={0.8} onPress={handleSubmit}>
          <ThemedText style={styles.submitButtonText}>제출하기</ThemedText>
        </TouchableOpacity>
      </ScrollView>

      {/* Success Modal */}
      <Modal visible={showSuccessModal} transparent animationType="fade">
        <View style={styles.successOverlay}>
          <View style={styles.successCard}>
            <View style={styles.successIconWrap}>
              <ThemedText style={styles.successEmoji}>🎉</ThemedText>
            </View>
            <ThemedText style={styles.successTitle}>신고가 접수되었습니다</ThemedText>
            <ThemedText style={styles.successPoints}>
              +{successPoints.toLocaleString()} 포인트가 추가되었습니다!
            </ThemedText>
            <ThemedText style={styles.successSubtext}>
              {GIFT_THRESHOLD.toLocaleString()}포인트를 모으면 스타벅스 아메리카노 기프티콘을 제공합니다.
            </ThemedText>
            {(() => {
              const { current } = getBadgeForPoints(totalPoints);
              return (
                <View style={styles.successBadgeRow}>
                  <ThemedText style={styles.successBadgeEmoji}>{current.icon}</ThemedText>
                  <ThemedText style={styles.successBadgeName}>{current.name}</ThemedText>
                </View>
              );
            })()}
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 32,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  closeButton: {
    padding: 4,
  },
  rewardSection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    gap: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  coinImage: {
    width: 60,
    height: 60,
  },
  rewardInfo: {
    flex: 1,
  },
  rewardLabel: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 4,
  },
  rewardAmount: {
    fontSize: 22,
    fontWeight: '700',
    color: ACCENT_GREEN_DARK,
  },
  badgeSection: {
    marginBottom: 24,
  },
  badgeSectionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginBottom: 12,
  },
  currentBadgeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    gap: 14,
  },
  badgeIconWrap: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(0, 207, 144, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeEmoji: {
    fontSize: 28,
  },
  badgeContent: {
    flex: 1,
  },
  badgeName: {
    fontSize: 17,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 4,
  },
  badgeDesc: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 18,
  },
  nextTierRow: {
    marginBottom: 14,
  },
  progressBarBg: {
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(0,0,0,0.08)',
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
    backgroundColor: ACCENT_GREEN,
  },
  nextTierText: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
  },
  nextTierName: {
    fontWeight: '600',
    color: ACCENT_GREEN_DARK,
  },
  rewardInfoList: {
    gap: 6,
  },
  rewardInfoItem: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 20,
  },
  inputSection: {
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  inputWrapper: {
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
  },
  input: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    fontSize: 16,
    color: TEXT_COLOR,
  },
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
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  historySubtitle: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 20,
    lineHeight: 20,
  },
  historyItem: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
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
  historyItemDate: {
    fontSize: 12,
    color: SECONDARY_TEXT_COLOR,
  },
  historyCancel: {
    marginTop: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  historyCancelText: {
    fontSize: 16,
    color: SECONDARY_TEXT_COLOR,
  },
  submitButton: {
    backgroundColor: ACCENT_GREEN,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
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
  successIconWrap: {
    marginBottom: 16,
  },
  successEmoji: {
    fontSize: 56,
  },
  successTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 12,
  },
  successPoints: {
    fontSize: 18,
    fontWeight: '700',
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
  successBadgeEmoji: {
    fontSize: 24,
  },
  successBadgeName: {
    fontSize: 16,
    fontWeight: '600',
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
  successButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
