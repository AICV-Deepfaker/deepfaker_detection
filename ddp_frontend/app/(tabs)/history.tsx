import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { useCallback } from 'react';
import { FlatList, StyleSheet, View, TouchableOpacity } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

const extractFakeProbPercent = (text?: string) => {
  if (!text) return null;

  const m = text.match(/딥페이크\s*확률\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%/);
  if (!m) return null;

  const n = Number(m[1]);
  if (!Number.isFinite(n)) return null;
  return Math.min(100, Math.max(0, n));
};

export default function HistoryScreen() {
  const insets = useSafeAreaInsets();
  const { history } = useAnalysis();

  const renderItem = useCallback(
    ({ item }: { item: (typeof history)[0] }) => {
      const isFake = item.resultType === 'FAKE';
      const isReal = item.resultType === 'REAL';

      // ✅ 딥페이크 확률 % 추출 (없으면 0)
      const percent = extractFakeProbPercent(item.result) ?? 0;

      return (
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => {
            router.push(`/history/${item.id}`);
          }}
        >
          <View style={styles.cardRow}>
            {/* 왼쪽 썸네일 */}
            <View style={styles.thumbCropBox}>
              {item.visualReport ? (
                <Image
                  source={{ uri: `data:image/png;base64,${item.visualReport}` }}
                  style={styles.thumbCroppedImage}
                  contentFit="cover"
                />
              ) : (
                <View style={styles.thumbFallback} />
              )}
            </View>

            {/* 오른쪽 내용 */}
            <View style={styles.rightContent}>
              {isFake && (
                <View style={[styles.badge, styles.badgeFake]}>
                  <MaterialIcons name="warning" size={16} color="#fff" />
                  <ThemedText style={styles.badgeText}>FAKE</ThemedText>
                </View>
              )}
              {isReal && (
                <View style={[styles.badge, styles.badgeReal]}>
                  <MaterialIcons name="check-circle" size={16} color="#fff" />
                  <ThemedText style={styles.badgeText}>REAL</ThemedText>
                </View>
              )}

              {/* ✅ 딥페이크 확률 바 */}
              <View style={styles.confRow}>
                <View style={styles.barTrack}>
                  <View
                    style={[
                      styles.barFill,
                      {
                        width: `${percent}%`,
                        backgroundColor: isFake ? '#FF6B6B' : '#7ED957',
                      },
                    ]}
                  />
                </View>
                <ThemedText style={styles.percentText}>{percent.toFixed(0)}%</ThemedText>
              </View>

              {/* 날짜 */}
              <ThemedText style={styles.itemDate}>
                {new Date(item.date).toLocaleString('ko-KR')}
              </ThemedText>
            </View>
          </View>
        </TouchableOpacity>
      );
    },
    [history],
  );

  const keyExtractor = useCallback((item: (typeof history)[0]) => item.id, []);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <ThemedText style={styles.headerTitle}>분석 히스토리</ThemedText>
        <ThemedText style={styles.headerSubtitle}>이전에 분석한 결과 목록입니다</ThemedText>
      </View>

      {history.length === 0 ? (
        <View style={styles.empty}>
          <MaterialIcons name="history" size={64} color={SECONDARY_TEXT_COLOR} />
          <ThemedText style={styles.emptyTitle}>분석 내역이 없습니다</ThemedText>
          <ThemedText style={styles.emptySubtitle}>
            링크나 파일을 챗봇으로 보내면{'\n'} 분석 결과가 여기에 저장됩니다
          </ThemedText>
        </View>
      ) : (
        <FlatList
          data={history}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + 24 }]}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },

  header: {
    paddingHorizontal: 20,
    paddingVertical: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: TEXT_COLOR },
  headerSubtitle: { fontSize: 14, color: SECONDARY_TEXT_COLOR, marginTop: 4 },

  list: { padding: 16 },

  cardRow: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,

    flexDirection: 'row',
    padding: 14,
    gap: 14,
  },

  thumbCropBox: {
    width: 110,
    height: 110,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.05)',
  },

  thumbCroppedImage: {
    width: '200%',
    height: '100%',
    transform: [{ translateX: 0 }],
  },

  thumbFallback: { flex: 1, backgroundColor: 'rgba(0,0,0,0.05)' },

  rightContent: { flex: 1, justifyContent: 'center', gap: 10 },

  confRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },

  barTrack: {
    flex: 1,
    height: 16,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.18)',
    overflow: 'hidden',
  },

  barFill: { height: '100%', borderRadius: 999 },

  percentText: {
    width: 44,
    textAlign: 'right',
    fontWeight: '700',
    color: TEXT_COLOR,
  },

  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  badgeFake: { backgroundColor: '#FF4444' },
  badgeReal: { backgroundColor: ACCENT_GREEN },
  badgeText: { color: '#fff', fontSize: 13, fontWeight: '700' },

  itemDate: { fontSize: 12, color: SECONDARY_TEXT_COLOR },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: TEXT_COLOR, marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: SECONDARY_TEXT_COLOR, marginTop: 8, textAlign: 'center' },
});