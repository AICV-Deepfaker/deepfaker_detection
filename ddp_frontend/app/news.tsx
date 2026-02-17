// npm i fast-xml-parser

import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Linking,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { fetchNewsByCategory, type NewsItem } from '@/lib/news';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

const NEWS_CATEGORIES = [
  { id: 'invest', label: '투자' },
  { id: 'gamble', label: '도박' },
  { id: 'coin', label: '코인' },
  { id: 'loan', label: '대출' },
  { id: 'remit', label: '송금' },
  { id: 'refund', label: '환급' },
] as const;

type CategoryId = (typeof NEWS_CATEGORIES)[number]['id'];

const PAGE_SIZE = 10;

export default function NewsScreen() {
  const insets = useSafeAreaInsets();
  const [selectedCategory, setSelectedCategory] = useState<CategoryId>('invest');

  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ✅ "더보기"용: 현재 화면에 보여줄 개수
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchNewsByCategory(selectedCategory);
      setItems(data);
    } catch (e) {
      setItems([]);
      setError(e instanceof Error ? e.message : '뉴스 로드 실패');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  // ✅ 카테고리 바뀌면 다시 10개부터
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [selectedCategory]);

  useEffect(() => {
    load();
  }, [load]);

  // ✅ 실제로 FlatList에 주는 데이터는 "보이는 만큼만"
  const visibleItems = useMemo(() => items.slice(0, visibleCount), [items, visibleCount]);

  const renderItem = useCallback(
    ({ item }: { item: NewsItem }) => (
      <TouchableOpacity
        activeOpacity={0.85}
        onPress={() => {
          if (item.link) Linking.openURL(item.link);
        }}
      >
        <View style={styles.newsItem}>
          <ThemedText style={styles.newsItemTitle} numberOfLines={2}>
            {item.title}
          </ThemedText>
          <ThemedText style={styles.newsItemDate}>
            {item.date}
            {item.source ? ` · ${item.source}` : ''}
          </ThemedText>
          <ThemedText style={styles.newsItemSummary} numberOfLines={2}>
            {item.summary}
          </ThemedText>
        </View>
      </TouchableOpacity>
    ),
    [],
  );

  const keyExtractor = useCallback(
    (item: NewsItem, index: number) => `${item.link ?? item.title}-${index}`,
    [],
  );

  // ✅ 더보기 버튼 (ListFooterComponent)
  const ListFooter = useMemo(() => {
    if (loading) return null;
    if (items.length <= visibleCount) return null;

    return (
      <TouchableOpacity
        activeOpacity={0.85}
        onPress={() => setVisibleCount((c) => c + PAGE_SIZE)}
        style={styles.loadMoreBtn}
      >
        <ThemedText style={styles.loadMoreText}>더보기</ThemedText>
        <ThemedText style={styles.loadMoreSub}>
          {visibleCount}/{items.length}
        </ThemedText>
      </TouchableOpacity>
    );
  }, [items.length, visibleCount, loading]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} hitSlop={12}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>딥페이크 금융사기 피해 뉴스</ThemedText>
        <View style={styles.headerRight} />
      </View>

      {/* Category tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={[styles.categoryScroll, { paddingHorizontal: 18 }]}
        style={styles.categoryScrollView}
      >
        {NEWS_CATEGORIES.map((cat) => {
          const isSelected = selectedCategory === cat.id;
          return (
            <TouchableOpacity
              key={cat.id}
              style={[styles.categoryChip, isSelected && styles.categoryChipSelected]}
              activeOpacity={0.8}
              onPress={() => setSelectedCategory(cat.id)}
            >
              <ThemedText style={[styles.categoryLabel, isSelected && styles.categoryLabelSelected]}>
                {cat.label}
              </ThemedText>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Body */}
      {loading ? (
        <View style={{ padding: 24, alignItems: 'center' }}>
          <ActivityIndicator size="large" color={ACCENT_GREEN} />
          <ThemedText style={{ marginTop: 10, color: SECONDARY_TEXT_COLOR }}>
            뉴스 불러오는 중...
          </ThemedText>
        </View>
      ) : (
        <FlatList
          data={visibleItems}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 24 }]}
          showsVerticalScrollIndicator={false}
          onRefresh={load}
          refreshing={loading}
          ListFooterComponent={ListFooter}
          ListEmptyComponent={
            <View style={styles.empty}>
              <ThemedText style={styles.emptyText}>
                {error ? error : '해당 카테고리 뉴스가 없습니다.'}
              </ThemedText>
            </View>
          }
        />
      )}
    </View>
  );
}

/* ✅ styles는 최대한 유지 + 더보기 버튼 스타일만 추가 */
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: TEXT_COLOR },
  headerRight: { width: 32 },

  categoryScrollView: { paddingVertical: 10, backgroundColor: '#fff' },
  categoryScroll: { paddingVertical: 8, gap: 10, flexDirection: 'row', alignItems: 'center' },
  categoryChip: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 22,
    minHeight: 36,
    backgroundColor: '#F0F0F0',
  },
  categoryChipSelected: { backgroundColor: ACCENT_GREEN },
  categoryLabel: {
    fontSize: 15,
    lineHeight: 16,
    fontWeight: '700',
    color: SECONDARY_TEXT_COLOR,
    includeFontPadding: false,
    textAlignVertical: 'center',
  },
  categoryLabelSelected: { color: '#fff' },

  listContent: { padding: 18 },
  newsItem: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  newsItemTitle: { fontSize: 16, fontWeight: '700', color: TEXT_COLOR, marginBottom: 8 },
  newsItemDate: { fontSize: 12, color: SECONDARY_TEXT_COLOR, marginBottom: 8 },
  newsItemSummary: { fontSize: 14, color: SECONDARY_TEXT_COLOR, lineHeight: 20 },

  empty: { padding: 40, alignItems: 'center' },
  emptyText: { fontSize: 15, color: SECONDARY_TEXT_COLOR, textAlign: 'center' },

  // ✅ 추가: 더보기 버튼
  loadMoreBtn: {
    marginTop: 8,
    alignSelf: 'center',
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 14,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  loadMoreText: {
    color: ACCENT_GREEN,
    fontWeight: '800',
    fontSize: 15,
  },
  loadMoreSub: {
    color: SECONDARY_TEXT_COLOR,
    fontWeight: '700',
    fontSize: 12,
  },
});