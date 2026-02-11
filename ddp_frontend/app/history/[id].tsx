import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';

const ACCENT_GREEN = '#00CF90';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

const extractConfidencePercent = (text?: string) => {
  if (!text) return null;
  const m = text.match(/분석\s*신뢰도\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%/);
  if (!m) return null;
  const n = Number(m[1]);
  if (!Number.isFinite(n)) return null;
  return Math.min(100, Math.max(0, n));
};

const formatKoreanDateTime = (d: string | number | Date) => {
  const date = new Date(d);
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getContentLabel = (item: any) => {
  // 프로젝트에 따라 필드명이 다를 수 있어서 최대한 커버
  const t =
    item?.contentType ||
    item?.inputType ||
    item?.sourceType ||
    item?.type ||
    item?.kind ||
    '';

  const s = String(t).toLowerCase();

  // 문자열 기반 타입
  if (s.includes('link') || s.includes('url')) return '링크';
  if (s.includes('video') || s.includes('mp4') || s.includes('mov')) return '영상 파일';
  if (s.includes('image') || s.includes('jpg') || s.includes('png') || s.includes('jpeg'))
    return '이미지 파일';

  // 값이 없을 때, url/파일명으로 유추
  const url = item?.url || item?.link || '';
  if (typeof url === 'string' && url.startsWith('http')) return '링크';

  const fileName = item?.fileName || item?.filename || '';
  const f = String(fileName).toLowerCase();
  if (f.match(/\.(mp4|mov|avi|mkv)$/)) return '영상 파일';
  if (f.match(/\.(jpg|jpeg|png|webp)$/)) return '이미지 파일';

  return '영상 파일';
};

export default function HistoryDetailScreen() {
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { history } = useAnalysis();

  const item = useMemo(() => history.find((h) => h.id === id), [history, id]);

  const isFake = item?.resultType === 'FAKE';
  const isReal = item?.resultType === 'REAL';
  const percent = extractConfidencePercent(item?.result) ?? 0;

  // 신고 여부 로컬 저장
  const storageKey = id ? `reported:${id}` : '';
  const [reported, setReported] = useState(false);

  useEffect(() => {
    if (!storageKey) return;
    (async () => {
      const v = await AsyncStorage.getItem(storageKey);
      setReported(v === '1');
    })();
  }, [storageKey]);

  const onPressReport = async () => {
    if (!storageKey) return;

    // ✅ fraud-report가 app/history/fraud-report.tsx 라면 이게 맞음
    router.push('app/fraud-report');

    await AsyncStorage.setItem(storageKey, '1');
    setReported(true);
  };

  if (!item) {
    return (
      <View style={styles.container}>
        <View style={styles.center}>
          <ThemedText style={{ color: SECONDARY_TEXT_COLOR }}>
            해당 히스토리를 찾을 수 없습니다.
          </ThemedText>
        </View>
      </View>
    );
  }

  const contentLabel = getContentLabel(item);

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        showsVerticalScrollIndicator={false}
      >
        {/* 1) 분석 정보 박스 */}
        <View style={styles.card}>
          <ThemedText style={styles.sectionTitle}>분석 정보</ThemedText>

          <View style={styles.infoRow}>
            <ThemedText style={styles.infoLabel}>분석 일시</ThemedText>
            <ThemedText style={styles.infoValue}>{formatKoreanDateTime(item.date)}</ThemedText>
          </View>

          <View style={styles.infoRow}>
            <ThemedText style={styles.infoLabel}>콘텐츠</ThemedText>
            <ThemedText style={styles.infoValue}>{contentLabel}</ThemedText>
          </View>
        </View>

        {/* 2) 판정 결과 박스 */}
        <View style={styles.card}>
          <ThemedText style={styles.sectionTitle}>판정 결과</ThemedText>

          <View style={styles.resultRow}>
            <View style={[styles.resultPill, isFake ? styles.pillFake : styles.pillReal]}>
              <MaterialIcons
                name={isFake ? 'warning' : 'check-circle'}
                size={18}
                color="#fff"
              />
              <ThemedText style={styles.pillText}>{isFake ? 'FAKE' : 'REAL'}</ThemedText>
            </View>

            <ThemedText style={styles.percentBig}>{Math.round(percent)}%</ThemedText>
          </View>

          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                { width: `${Math.round(percent)}%`, backgroundColor: isFake ? '#FF6B6B' : '#7ED957' },
              ]}
            />
          </View>

          <ThemedText style={styles.percentCaption}>
            {isFake ? '딥페이크/사기 의심 확률' : '정상 콘텐츠로 판단될 확률'}
          </ThemedText>
        </View>

        {/* 3) 시각화 리포트 */}
        {item.visualReport ? (
          <View style={styles.imageCard}>
            <ThemedText style={styles.sectionTitle}>시각화 리포트</ThemedText>
            <Image
              source={{ uri: `data:image/png;base64,${item.visualReport}` }}
              style={styles.fullReportImage}
              contentFit="contain"
              cachePolicy="memory-disk"
            />
          </View>
        ) : (
          <View style={styles.imageCard}>
            <ThemedText style={styles.sectionTitle}>시각화 리포트</ThemedText>
            <ThemedText style={{ color: SECONDARY_TEXT_COLOR }}>시각화 리포트가 없습니다.</ThemedText>
          </View>
        )}

        {/* 4) 분석 결과 텍스트 */}
        <View style={styles.textCard}>
          <ThemedText style={styles.sectionTitle}>분석 결과</ThemedText>
          <ThemedText style={styles.resultText}>
            {item.result || '분석 결과 텍스트가 없습니다.'}
          </ThemedText>
        </View>

        {/* ✅ 신고 버튼 */}
        <View style={styles.buttonWrap}>
          {reported ? (
            <View style={[styles.reportButton, styles.reportDone]}>
              <MaterialIcons name="check-circle" size={20} color="#fff" />
              <ThemedText style={styles.reportButtonText}>신고 완료</ThemedText>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.reportButton}
              activeOpacity={0.85}
              onPress={onPressReport}
            >
              <MaterialIcons name="report" size={20} color="#fff" />
              <ThemedText style={styles.reportButtonText}>신고하기</ThemedText>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  scroll: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  card: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },

  sectionTitle: { fontSize: 16, fontWeight: '700', color: TEXT_COLOR, marginBottom: 12 },

  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#E6E8EA',
  },
  infoLabel: { color: SECONDARY_TEXT_COLOR, fontSize: 14 },
  infoValue: { color: TEXT_COLOR, fontSize: 14, fontWeight: '700' },

  resultRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  resultPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 999,
  },
  pillFake: { backgroundColor: '#FF2D2D' },
  pillReal: { backgroundColor: ACCENT_GREEN },
  pillText: { color: '#fff', fontSize: 20, fontWeight: '900', letterSpacing: 0.5 },

  percentBig: { fontSize: 28, fontWeight: '900', color: TEXT_COLOR },

  progressTrack: {
    height: 16,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.12)',
    overflow: 'hidden',
  },
  progressFill: { height: '100%', borderRadius: 999 },

  percentCaption: { marginTop: 10, color: SECONDARY_TEXT_COLOR, fontSize: 13 },

  imageCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  fullReportImage: {
    width: '100%',
    height: 240,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },

  textCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  resultText: {
    fontSize: 14,
    color: TEXT_COLOR,
    lineHeight: 20,
    // RN에서는 whiteSpace 무시됨 (기존 코드 제거)
  },

  buttonWrap: { marginHorizontal: 16, marginBottom: 16 },
  reportButton: {
    backgroundColor: ACCENT_GREEN,
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  reportDone: { backgroundColor: 'rgba(0,0,0,0.35)' },
  reportButtonText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});