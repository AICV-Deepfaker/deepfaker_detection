import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  FlatList,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';

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

/** 카테고리별 placeholder 뉴스 (추후 API 연동 시 교체) */
const PLACEHOLDER_ITEMS: Record<CategoryId, { title: string; date: string; summary: string }[]> = {
  invest: [
    { title: '유명인 사칭 투자 사기, 1년간 1천200억 피해', date: '2025.02.10', summary: '딥페이크 영상을 이용한 투자 사기 사례가 급증하고 있습니다.' },
    { title: '"고수익 보장" 메신저 사기 주의보', date: '2025.02.08', summary: '손흥민·연예인 사칭 영상으로 신뢰 유도 후 자금 편취.' },
  ],
  gamble: [
    { title: '"강원랜드 사칭" 앱 피싱, 수백 명 피해', date: '2025.02.09', summary: '가짜 앱 설치 유도 후 개인정보·자금 탈취 수법.' },
    { title: '도박 사이트 가입 권유 딥페이크 영상 주의', date: '2025.02.05', summary: '유명인 합성 영상으로 불법 도박 사이트 유도.' },
  ],
  coin: [
    { title: '가상자산 투자 사기, 딥페이크로 신뢰도 부여', date: '2025.02.07', summary: '코인·NFT 투자 권유 시 합성 영상 활용 사례.' },
    { title: '암호화폐 스캠 피해 30% 증가', date: '2025.02.03', summary: '유명인 사칭 영상을 통한 코인 사기 주의.' },
  ],
  loan: [
    { title: '대출 사기, "무담보 즉시 대출" 딥페이크 광고', date: '2025.02.06', summary: '가짜 연예인·금융인 영상으로 대출 사이트 유도.' },
    { title: '신용대출 사기 수법에 딥페이크 활용', date: '2025.02.01', summary: '합성 영상으로 정당한 대출처럼 보이게 유도.' },
  ],
  remit: [
    { title: '송금 유도 사기, "긴급 송금" 딥페이크 영상', date: '2025.02.04', summary: '지인·공인 사칭 영상으로 즉시 송금 요구.' },
    { title: '해외 송금 사기 피해 급증', date: '2025.01.28', summary: '유명인 목소리·얼굴 합성으로 송금 요청.' },
  ],
  refund: [
    { title: '"환급·보상금" 사기, 딥페이크로 공식처럼 위장', date: '2025.02.02', summary: '가짜 고객센터·공인 영상으로 선입금 요구.' },
    { title: '피해 환급 사칭 사기 주의보', date: '2025.01.25', summary: '경찰·금융당국 사칭 영상으로 추가 피해 유도.' },
  ],
};

export default function NewsScreen() {
  const insets = useSafeAreaInsets();
  const [selectedCategory, setSelectedCategory] = useState<CategoryId>('invest');

  const items = PLACEHOLDER_ITEMS[selectedCategory];

  const renderItem = useCallback(
    ({ item }: { item: (typeof items)[0] }) => (
      <View style={styles.newsItem}>
        <ThemedText style={styles.newsItemTitle} numberOfLines={2}>
          {item.title}
        </ThemedText>
        <ThemedText style={styles.newsItemDate}>{item.date}</ThemedText>
        <ThemedText style={styles.newsItemSummary} numberOfLines={2}>
          {item.summary}
        </ThemedText>
      </View>
    ),
    [],
  );

  const keyExtractor = useCallback((item: (typeof items)[0], index: number) => `${item.title}-${index}`, []);

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
        style={styles.categoryScrollView}>
        {NEWS_CATEGORIES.map((cat) => {
          const isSelected = selectedCategory === cat.id;
          return (
            <TouchableOpacity
              key={cat.id}
              style={[styles.categoryChip, isSelected && styles.categoryChipSelected]}
              activeOpacity={0.8}
              onPress={() => setSelectedCategory(cat.id)}>
              <ThemedText style={[styles.categoryLabel, isSelected && styles.categoryLabelSelected]}>
                {cat.label}
              </ThemedText>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* News list */}
      <FlatList
        data={items}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.empty}>
            <ThemedText style={styles.emptyText}>해당 카테고리 뉴스가 없습니다.</ThemedText>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
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
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  headerRight: {
    width: 32,
  },
  categoryScrollView: {
    maxHeight: 52,
    backgroundColor: '#fff',
  },
  categoryScroll: {
    paddingVertical: 12,
    gap: 10,
    flexDirection: 'row',
  },
  categoryChip: {
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#F0F0F0',
  },
  categoryChipSelected: {
    backgroundColor: ACCENT_GREEN,
  },
  categoryLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
  },
  categoryLabelSelected: {
    color: '#fff',
  },
  listContent: {
    padding: 18,
  },
  newsItem: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  newsItemTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  newsItemDate: {
    fontSize: 12,
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 8,
  },
  newsItemSummary: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 20,
  },
  empty: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 15,
    color: SECONDARY_TEXT_COLOR,
  },
});
