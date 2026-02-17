import AsyncStorage from '@react-native-async-storage/async-storage';
import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useFocusEffect, router } from 'expo-router';
import React, { useCallback, useMemo, useState } from 'react';
import { FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis, getBadgeForPoints, GIFT_THRESHOLD } from '@/contexts/analysis-context';

export default function ReportHistoryScreen() {
  const insets = useSafeAreaInsets();
  const { history, totalPoints } = useAnalysis();
  const { current, next } = getBadgeForPoints(totalPoints);

  const [reportedIds, setReportedIds] = useState<Record<string, boolean>>({});

  useFocusEffect(
    useCallback(() => {
      let mounted = true;

      (async () => {
        // history가 많지 않다는 전제에서: Promise.all로 한번에 체크
        const pairs = await Promise.all(
          history.map(async (h) => {
            const v = await AsyncStorage.getItem(`reported:${h.id}`);
            return [h.id, v === '1'] as const;
          })
        );

        if (!mounted) return;
        const map: Record<string, boolean> = {};
        for (const [id, ok] of pairs) map[id] = ok;
        setReportedIds(map);
      })();

      return () => {
        mounted = false;
      };
    }, [history])
  );

  const reportedList = useMemo(
    () => history.filter((h) => reportedIds[h.id]),
    [history, reportedIds]
  );

  const progressToNext =
    next && next.minPoints > totalPoints
      ? Math.min(
          100,
          ((totalPoints - current.minPoints) / (next.minPoints - current.minPoints)) * 100
        )
      : 100;

  const nextPointsNeeded = next ? Math.max(0, next.minPoints - totalPoints) : 0;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <ThemedText style={styles.headerTitle}>신고내역</ThemedText>
        <ThemedText style={styles.headerSub}>신고 완료한 기록만 모아봤어요</ThemedText>
      </View>

      {/* ✅ 리워드/등급 카드 */}
      <View style={styles.rewardCard}>
        <View style={styles.rewardTop}>
          <View style={styles.badgeIcon}>
            <ThemedText style={styles.badgeEmoji}>{current.icon}</ThemedText>
          </View>
          <View style={{ flex: 1 }}>
            <ThemedText style={styles.rewardLabel}>보유 포인트</ThemedText>
            <ThemedText style={styles.rewardPoints}>{totalPoints.toLocaleString()} P</ThemedText>
            <ThemedText style={styles.rewardTier}>
              현재 등급: <ThemedText style={styles.rewardTierBold}>{current.name}</ThemedText>
            </ThemedText>
            <ThemedText style={styles.rewardDesc}>{current.desc}</ThemedText>
          </View>
        </View>

        {next && nextPointsNeeded > 0 && (
          <View style={{ marginTop: 12 }}>
            <View style={styles.progressBg}>
              <View style={[styles.progressFill, { width: `${progressToNext}%` }]} />
            </View>
            <ThemedText style={styles.nextTierText}>
              다음 등급 <ThemedText style={styles.nextTierBold}>{next.name}</ThemedText>까지{' '}
              {nextPointsNeeded.toLocaleString()}P
            </ThemedText>
          </View>
        )}

        <View style={{ marginTop: 10 }}>
          <ThemedText style={styles.rewardHint}>
            🎁 {GIFT_THRESHOLD.toLocaleString()}P 달성 시 스타벅스 아메리카노 기프티콘
          </ThemedText>
          <ThemedText style={styles.rewardHint}>🏅 100,000P 달성 시 경찰청장상 수상급</ThemedText>
        </View>
      </View>

      {reportedList.length === 0 ? (
        <View style={styles.empty}>
          <MaterialIcons name="report" size={56} color="#687076" />
          <ThemedText style={styles.emptyTitle}>신고 완료한 내역이 없습니다</ThemedText>
          <ThemedText style={styles.emptySub}>히스토리 상세에서 신고를 완료하면 여기에 뜹니다</ThemedText>
        </View>
      ) : (
        <FlatList
          data={reportedList}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 24 }}
          renderItem={({ item }) => (
            <TouchableOpacity
              activeOpacity={0.85}
              onPress={() => router.push(`/history/${item.id}`)}
              style={styles.card}
            >
              <ThemedText style={styles.cardTitle}>신고 완료</ThemedText>
              <ThemedText style={styles.cardDate}>
                {new Date(item.date).toLocaleString('ko-KR')}
              </ThemedText>
              <ThemedText style={styles.cardResult} numberOfLines={2}>
                {item.result}
              </ThemedText>
            </TouchableOpacity>
          )}
        />
      )}
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
  headerTitle: { fontSize: 22, fontWeight: '800', color: '#111' },
  headerSub: { marginTop: 4, fontSize: 13, color: '#687076' },

  rewardCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    padding: 16,
    margin: 16,
  },
  rewardTop: { flexDirection: 'row', gap: 14, alignItems: 'center' },
  badgeIcon: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: 'rgba(0, 207, 144, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeEmoji: { fontSize: 28 },
  rewardLabel: { fontSize: 13, color: '#687076', marginBottom: 4 },
  rewardPoints: { fontSize: 22, fontWeight: '900', color: '#00B87A', marginBottom: 6 },
  rewardTier: { fontSize: 13, color: '#111', marginBottom: 2 },
  rewardTierBold: { fontWeight: '900', color: '#00B87A' },
  rewardDesc: { fontSize: 12, color: '#687076', lineHeight: 18 },

  progressBg: {
    height: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.10)',
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: { height: '100%', borderRadius: 999, backgroundColor: '#00CF90' },
  nextTierText: { fontSize: 12, color: '#687076' },
  nextTierBold: { fontWeight: '800', color: '#00B87A' },
  rewardHint: { fontSize: 12, color: '#687076', lineHeight: 18 },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: { marginTop: 12, fontSize: 16, fontWeight: '700', color: '#111' },
  emptySub: { marginTop: 6, fontSize: 13, color: '#687076', textAlign: 'center' },

  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    marginBottom: 12,
  },
  cardTitle: { fontSize: 14, fontWeight: '800', color: '#00B87A', marginBottom: 6 },
  cardDate: { fontSize: 12, color: '#687076', marginBottom: 8 },
  cardResult: { fontSize: 13, color: '#111', lineHeight: 18 },
});