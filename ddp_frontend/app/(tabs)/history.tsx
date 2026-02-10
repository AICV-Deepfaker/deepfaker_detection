import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { useCallback } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function HistoryScreen() {
  const insets = useSafeAreaInsets();
  const { history } = useAnalysis();

  const renderItem = useCallback(({ item }: { item: (typeof history)[0] }) => {
    const isFake = item.resultType === 'FAKE';
    const isReal = item.resultType === 'REAL';
    return (
      <View style={styles.card}>
        {/* 썸네일 이미지 */}
        {item.visualReport && (
          <Image
            source={{ uri: `data:image/png;base64,${item.visualReport}` }}
            style={styles.thumbnail}
            contentFit="cover"
            cachePolicy="memory-disk"
          />
        )}
        <View style={styles.cardContent}>
          {/* 결과 배지 */}
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
          {/* 링크/파일명 */}
          <View style={styles.itemHeader}>
            <MaterialIcons name="link" size={18} color={ACCENT_GREEN} />
            <ThemedText style={styles.itemLink} numberOfLines={1}>
              {item.link}
            </ThemedText>
          </View>
          {/* 결과 요약 */}
          <ThemedText style={styles.itemResult} numberOfLines={3}>
            {item.result.split('\n')[0]}
          </ThemedText>
          {/* 날짜 */}
          <ThemedText style={styles.itemDate}>
            {new Date(item.date).toLocaleDateString('ko-KR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </ThemedText>
        </View>
      </View>
    );
  }, []);

  const keyExtractor = useCallback((item: (typeof history)[0]) => item.id, []);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <ThemedText style={styles.headerTitle}>분석 히스토리</ThemedText>
        <ThemedText style={styles.headerSubtitle}>
          이전에 분석한 결과 목록입니다
        </ThemedText>
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
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
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
  list: {
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  thumbnail: {
    width: '100%',
    height: 180,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  cardContent: {
    padding: 16,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    marginBottom: 12,
  },
  badgeFake: {
    backgroundColor: '#FF4444',
  },
  badgeReal: {
    backgroundColor: ACCENT_GREEN,
  },
  badgeText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
  itemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  itemLink: {
    flex: 1,
    fontSize: 14,
    color: ACCENT_GREEN,
    fontWeight: '600',
  },
  itemResult: {
    fontSize: 14,
    color: TEXT_COLOR,
    lineHeight: 20,
    marginBottom: 8,
  },
  itemDate: {
    fontSize: 12,
    color: SECONDARY_TEXT_COLOR,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 8,
    textAlign: 'center',
  },
});
