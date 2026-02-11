import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function HistoryReportScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ id: string }>();
  const { history } = useAnalysis();

  const item = useMemo(
    () => (params.id ? history.find((h) => h.id === params.id) : null),
    [history, params.id],
  );

  if (!item) {
    return (
      <View style={[styles.container, { paddingTop: insets.top + 20, paddingHorizontal: 20 }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backRow}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
          <ThemedText style={styles.backText}>뒤로</ThemedText>
        </TouchableOpacity>
        <ThemedText style={styles.emptyMessage}>해당 분석 항목을 찾을 수 없습니다.</ThemedText>
      </View>
    );
  }

  const isFake = item.resultType === 'FAKE';
  const isReal = item.resultType === 'REAL';
  const dateLabel = new Date(item.date).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* 헤더 */}
      <View style={[styles.header, { paddingTop: 12, paddingBottom: 16 }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backRow} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
          <ThemedText style={styles.backText}>뒤로</ThemedText>
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>분석 리포트</ThemedText>
        <ThemedText style={styles.headerSubtitle}>분석 결과 요약</ThemedText>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 32 }]}
        showsVerticalScrollIndicator={false}>
        {/* 분석 정보 카드 */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>📋 분석 정보</ThemedText>
          <View style={styles.card}>
            <View style={styles.infoRow}>
              <ThemedText style={styles.infoLabel}>분석 일시</ThemedText>
              <ThemedText style={styles.infoValue}>{dateLabel}</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <ThemedText style={styles.infoLabel}>콘텐츠</ThemedText>
              <ThemedText style={[styles.infoValue, styles.linkText]} numberOfLines={2}>
                {item.link}
              </ThemedText>
            </View>
          </View>
        </View>

        {/* 판정 결과 */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>📊 판정 결과</ThemedText>
          <View
            style={[
              styles.verdictCard,
              isFake && styles.verdictFake,
              isReal && styles.verdictReal,
              !isFake && !isReal && styles.verdictNeutral,
            ]}>
            {isFake && (
              <>
                <MaterialIcons name="warning" size={32} color="#fff" />
                <ThemedText style={styles.verdictText}>딥페이크/금융사기 의심</ThemedText>
                <ThemedText style={styles.verdictSub}>FAKE</ThemedText>
              </>
            )}
            {isReal && (
              <>
                <MaterialIcons name="check-circle" size={32} color="#fff" />
                <ThemedText style={styles.verdictText}>정상 콘텐츠로 판단</ThemedText>
                <ThemedText style={styles.verdictSub}>REAL</ThemedText>
              </>
            )}
            {!isFake && !isReal && (
              <>
                <MaterialIcons name="help-outline" size={32} color={SECONDARY_TEXT_COLOR} />
                <ThemedText style={[styles.verdictText, styles.verdictTextMuted]}>판정 없음</ThemedText>
              </>
            )}
          </View>
        </View>

        {/* 시각화 */}
        {item.visualReport && (
          <View style={styles.section}>
            <ThemedText style={styles.sectionTitle}>🖼 시각화 결과</ThemedText>
            <View style={styles.card}>
              <Image
                source={{ uri: `data:image/png;base64,${item.visualReport}` }}
                style={styles.visualImage}
                contentFit="contain"
                cachePolicy="memory-disk"
              />
            </View>
          </View>
        )}

        {/* 상세 결과 전문 */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>📄 상세 결과</ThemedText>
          <View style={styles.card}>
            <ThemedText style={styles.detailText} selectable>
              {item.result}
            </ThemedText>
          </View>
        </View>
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
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  backRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 12,
  },
  backText: {
    fontSize: 16,
    color: TEXT_COLOR,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  headerSubtitle: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 4,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginBottom: 12,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  infoRow: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  infoLabel: {
    width: 90,
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
  },
  infoValue: {
    flex: 1,
    fontSize: 14,
    color: TEXT_COLOR,
    fontWeight: '500',
  },
  linkText: {
    color: ACCENT_GREEN,
  },
  verdictCard: {
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  verdictFake: {
    backgroundColor: '#FF4444',
  },
  verdictReal: {
    backgroundColor: ACCENT_GREEN,
  },
  verdictNeutral: {
    backgroundColor: '#E0E0E0',
  },
  verdictText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginTop: 12,
  },
  verdictTextMuted: {
    color: SECONDARY_TEXT_COLOR,
  },
  verdictSub: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    marginTop: 4,
  },
  visualImage: {
    width: '100%',
    height: 240,
    borderRadius: 12,
  },
  detailText: {
    fontSize: 14,
    color: TEXT_COLOR,
    lineHeight: 22,
  },
  emptyMessage: {
    fontSize: 16,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 20,
  },
});
