import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  Share,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import ViewShot from 'react-native-view-shot';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Clipboard from 'expo-clipboard';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { predictWithFile, predictWithVideoId, type PredictMode, type PredictResult, type SttSearchResult } from '@/lib/api';
import { takePendingVideoUri } from '@/lib/pending-upload';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const FAKE_RED = '#E53935';
const REAL_GREEN = '#43A047';
const TEXT = '#111';
const SUB = '#687076';
const CARD_BG = '#F8FAF9';
const BORDER = '#E8ECEE';

const STT_KEYWORDS = ['투자', '도박', '코인', '대출', '송금', '환급'];

function ResultBadge({ result }: { result: 'FAKE' | 'REAL' }) {
  const isFake = result === 'FAKE';
  return (
    <View style={[styles.badge, isFake ? styles.badgeFake : styles.badgeReal]}>
      <MaterialIcons name={isFake ? 'warning' : 'check-circle'} size={18} color="#fff" />
      <ThemedText style={styles.badgeText}>{result}</ThemedText>
    </View>
  );
}

function SectionCard({
  title,
  result,
  probability,
  confidenceScore,
  accuracy,
  visualBase64,
  children,
}: {
  title: string;
  result?: 'FAKE' | 'REAL';
  probability?: number;
  confidenceScore?: string;
  accuracy?: string;
  visualBase64?: string;
  children?: React.ReactNode;
}) {
  return (
    <View style={styles.sectionCard}>
      <ThemedText style={styles.sectionTitle}>{title}</ThemedText>

      {result != null && <ResultBadge result={result} />}

      <View style={styles.metricsRow}>
        {probability != null && (
          <View style={styles.metric}>
            <ThemedText style={styles.metricLabel}>확률</ThemedText>
            <ThemedText style={styles.metricValue}>{(probability * 100).toFixed(2)}%</ThemedText>
          </View>
        )}

        {confidenceScore != null && (
          <View style={styles.metric}>
            <ThemedText style={styles.metricLabel}>Confidence</ThemedText>
            <ThemedText style={styles.metricValue}>{confidenceScore}</ThemedText>
          </View>
        )}

        {accuracy != null && (
          <View style={styles.metric}>
            <ThemedText style={styles.metricLabel}>정확도</ThemedText>
            <ThemedText style={styles.metricValue}>{accuracy}</ThemedText>
          </View>
        )}
      </View>

      {visualBase64 ? (
        <View style={styles.visualWrap}>
          <Image
            source={{ uri: `data:image/png;base64,${visualBase64}` }}
            style={styles.visualImage}
            contentFit="contain"
          />
        </View>
      ) : null}

      {children}
    </View>
  );
}

function SttKeywordsCard({ keywords }: { keywords: { keyword: string; detected: boolean }[] }) {
  const list = keywords.length ? keywords : STT_KEYWORDS.map((k) => ({ keyword: k, detected: false }));

  return (
    <View style={styles.sectionCard}>
      <ThemedText style={styles.sectionTitle}>STT 키워드</ThemedText>
      <View style={styles.keywordGrid}>
        {list.map(({ keyword, detected }) => (
          <View key={keyword} style={[styles.keywordChip, detected && styles.keywordChipDetected]}>
            <ThemedText style={[styles.keywordText, detected && styles.keywordTextDetected]}>
              {keyword}
            </ThemedText>
            <ThemedText style={styles.keywordStatus}>{detected ? '감지됨' : '미감지'}</ThemedText>
          </View>
        ))}
      </View>
    </View>
  );
}

const RISK_COLOR: Record<string, string> = {
  high: '#E53935',
  medium: '#FB8C00',
  low: '#43A047',
  none: '#90A4AE',
};
const RISK_LABEL: Record<string, string> = {
  high: '위험',
  medium: '주의',
  low: '낮음',
  none: '해당없음',
};

function SttAnalysisCard({
  riskLevel,
  riskReason,
  transcript,
  searchResults,
}: {
  riskLevel?: string;
  riskReason?: string;
  transcript?: string;
  searchResults?: SttSearchResult[];
}) {
  if (!riskLevel && !transcript) return null;

  const color = RISK_COLOR[riskLevel ?? 'none'] ?? '#90A4AE';
  const label = RISK_LABEL[riskLevel ?? 'none'] ?? riskLevel;

  return (
    <View style={styles.sectionCard}>
      <ThemedText style={styles.sectionTitle}>STT 사기 분석</ThemedText>

      {riskLevel && (
        <View style={[styles.riskBadge, { backgroundColor: color }]}>
          <ThemedText style={styles.riskBadgeText}>위험도: {label?.toUpperCase()}</ThemedText>
        </View>
      )}

      {riskReason ? (
        <ThemedText style={styles.riskReason}>{riskReason}</ThemedText>
      ) : null}

      {transcript ? (
        <View style={styles.transcriptBox}>
          <ThemedText style={styles.transcriptLabel}>전사 텍스트</ThemedText>
          <ThemedText style={styles.transcriptText}>{transcript}</ThemedText>
        </View>
      ) : null}

      {searchResults && searchResults.length > 0 ? (
        <View style={styles.searchSection}>
          <ThemedText style={styles.transcriptLabel}>관련 최신 사례</ThemedText>
          {searchResults.map((item, i) => (
            <View key={i} style={styles.searchItem}>
              <ThemedText style={styles.searchKeyword}>[{item.keyword}]</ThemedText>
              <ThemedText style={styles.searchTitle}>{item.title}</ThemedText>
              <ThemedText style={styles.searchContent} numberOfLines={3}>
                {item.content}
              </ThemedText>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

export default function AnalysisResultScreen() {
  const insets = useSafeAreaInsets();

  const params = useLocalSearchParams<{ mode?: string; pendingVideo?: string; videoId?: string }>();
  const mode = (params.mode === 'fast' ? 'fast' : 'deep') as PredictMode;
  const videoId = params.videoId ?? null;
  const isEvidence = mode === 'fast';

  const { addToHistory } = useAnalysis();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictResult | null>(null);

  const viewShotRef = useRef<ViewShot>(null);

  // ✅ pending uri는 "한 번만" 가져오도록 ref에 고정 (렌더마다 바뀌면 꼬임)
  const initialVideoRef = useRef<string | null>(null);
  if (initialVideoRef.current === null) {
    initialVideoRef.current = takePendingVideoUri();
  }

  const mediaUri = initialVideoRef.current ?? null;

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let res: PredictResult;

      if (videoId) {
        // video_id 기반 분석 (링크 또는 S3 업로드된 영상)
        res = await predictWithVideoId(videoId, mode);
      } else if (mediaUri) {
        // 로컬 파일 기반 분석 (기존 플로우 - pendingVideo)
        res = await predictWithFile(mediaUri, mode);
      } else {
        setError('분석할 영상 정보가 없습니다.');
        setLoading(false);
        return;
      }

      if (res.status === 'error') {
        setError(res.message ?? '분석 실패');
        setData(null);
        return;
      }

      setData(res);

      const newId = addToHistory(
        '영상 파일',
        formatResultText(res),
        res.result,
        res.visual_report
      );

      if (!newId) return;

      setTimeout(() => {
        router.replace({
          pathname: '/history/[id]',
          params: { id: newId },
        });
      }, 0);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '네트워크 오류';
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [videoId, mediaUri, mode, addToHistory]);

  useEffect(() => {
    runAnalysis();
  }, [runAnalysis]);

  const handleShare = useCallback(async () => {
    if (!data) return;
    try {
      await Share.share({
        message: formatResultText(data),
        title: 'DDP 딥페이크 분석 결과',
      });
    } catch (_) {}
  }, [data]);

  const handleCopy = useCallback(async () => {
    if (!data) return;
    await Clipboard.setStringAsync(formatResultText(data));
    Alert.alert('복사됨', '결과가 클립보드에 복사되었습니다.');
  }, [data]);

  const handleSavePng = useCallback(async () => {
    const ref = viewShotRef.current as { capture?: () => Promise<string> } | null;
    if (!ref?.capture) return;

    try {
      const uri = await ref.capture();
      const fileUri = uri.startsWith('file://') ? uri : `file://${uri}`;

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: 'image/png' });
      } else {
        Alert.alert('저장', '이미지를 공유하여 저장할 수 있습니다.');
      }
    } catch (e) {
      Alert.alert('저장 실패', e instanceof Error ? e.message : 'PNG 저장에 실패했습니다.');
    }
  }, []);

  const handleSavePdf = useCallback(async () => {
    if (!data) return;
    try {
      const html = buildResultHtml(data, isEvidence);
      const { uri } = await Print.printToFileAsync({ html });

      if (uri && (await Sharing.isAvailableAsync())) {
        await Sharing.shareAsync(uri, { mimeType: 'application/pdf' });
      }
    } catch (e) {
      Alert.alert('저장 실패', e instanceof Error ? e.message : 'PDF 저장에 실패했습니다.');
    }
  }, [data, isEvidence]);

  // ✅ 로딩/에러 UI (분석 페이지가 잠깐 보일 때만)
  if (loading) {
    return (
      <View style={[styles.centered, { paddingTop: insets.top + 60 }]}>
        <ActivityIndicator size="large" color={ACCENT_GREEN} />
        <ThemedText style={styles.loadingText}>분석 중...</ThemedText>
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={[styles.centered, { paddingTop: insets.top + 60 }]}>
        <MaterialIcons name="error-outline" size={48} color={FAKE_RED} />
        <ThemedText style={styles.errorText}>{error ?? '결과를 불러올 수 없습니다.'}</ThemedText>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <ThemedText style={styles.backButtonText}>돌아가기</ThemedText>
        </TouchableOpacity>
      </View>
    );
  }

  const prob = data.average_fake_prob ?? 0;
  const conf = data.confidence_score ?? '-';
  const result = data.result;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBack}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>
          {isEvidence ? '증거수집모드 결과' : '정밀탐지모드 결과'}
        </ThemedText>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 120 }]}
        showsVerticalScrollIndicator={false}
      >
        <ViewShot ref={viewShotRef} options={{ format: 'png', quality: 1 }} style={styles.shotWrap}>
          {isEvidence ? (
            <>
              <SectionCard
                title="주파수"
                result={data.frequency?.result ?? result}
                probability={data.frequency?.probability ?? prob}
                confidenceScore={data.frequency?.confidence_score ?? conf}
                accuracy={data.frequency?.accuracy}
                visualBase64={data.frequency?.visual_base64 ?? data.visual_report}
              />
              <SectionCard
                title="rPPG"
                result={data.rppg?.result ?? result}
                probability={data.rppg?.probability ?? prob}
                confidenceScore={data.rppg?.confidence_score ?? conf}
                accuracy={data.rppg?.accuracy}
                visualBase64={data.rppg?.visual_base64}
              />
              <SttKeywordsCard keywords={data.stt_keywords ?? []} />
              <SttAnalysisCard
                riskLevel={data.stt_risk_level}
                riskReason={data.stt_risk_reason}
                transcript={data.stt_transcript}
                searchResults={data.stt_search_results}
              />
            </>
          ) : (
            <SectionCard
              title="UNITE"
              result={data.unite?.result ?? result}
              probability={data.unite?.probability ?? prob}
              confidenceScore={data.unite?.confidence_score ?? conf}
              accuracy={data.unite?.accuracy}
            />
          )}
        </ViewShot>

        {/* 공유/저장 */}
        <View style={styles.actionsSection}>
          <ThemedText style={styles.actionsSectionTitle}>결과 공유 및 저장</ThemedText>

          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
              <MaterialIcons name="share" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>공유하기</ThemedText>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} onPress={handleCopy}>
              <MaterialIcons name="content-copy" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>복사하기</ThemedText>
            </TouchableOpacity>
          </View>

          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.actionButton} onPress={handleSavePng}>
              <MaterialIcons name="image" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>PNG 저장</ThemedText>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} onPress={handleSavePdf}>
              <MaterialIcons name="picture-as-pdf" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>PDF 저장</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

function formatResultText(data: PredictResult): string {
  const r = data.result ?? '-';
  const p = data.average_fake_prob != null ? (data.average_fake_prob * 100).toFixed(2) : '-';
  const c = data.confidence_score ?? '-';
  return `[DDP 분석 결과]\n판정: ${r}\n딥페이크 확률: ${p}%\n신뢰도: ${c}`;
}

function buildResultHtml(data: PredictResult, isEvidence: boolean): string {
  const r = data.result ?? '-';
  const p = data.average_fake_prob != null ? (data.average_fake_prob * 100).toFixed(2) : '-';
  const c = data.confidence_score ?? '-';

  const img = data.visual_report
    ? `<img src="data:image/png;base64,${data.visual_report}" style="max-width:100%;height:auto;" />`
    : '';

  const modeLabel = isEvidence ? '증거수집모드' : '정밀탐지모드';

  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>DDP 분석 결과</title></head>
<body style="font-family:sans-serif;padding:20px;color:#111;">
  <h2>DDP 딥페이크 분석 결과 (${modeLabel})</h2>
  <p><strong>판정:</strong> ${r} &nbsp; <strong>확률:</strong> ${p}% &nbsp; <strong>신뢰도:</strong> ${c}</p>
  ${img}
</body>
</html>`;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },

  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 24,
  },

  loadingText: { marginTop: 12, fontSize: 16, color: SUB },
  errorText: { marginTop: 12, fontSize: 16, color: TEXT, textAlign: 'center' },

  backButton: {
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: ACCENT_GREEN,
    borderRadius: 12,
  },
  backButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: BORDER,
  },
  headerBack: { padding: 8 },
  headerTitle: { flex: 1, fontSize: 18, fontWeight: '700', color: TEXT, textAlign: 'center' },

  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  shotWrap: { backgroundColor: '#fff' },

  sectionCard: {
    backgroundColor: CARD_BG,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: BORDER,
  },

  sectionTitle: { fontSize: 16, fontWeight: '700', color: TEXT, marginBottom: 10 },

  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  badgeFake: { backgroundColor: FAKE_RED },
  badgeReal: { backgroundColor: REAL_GREEN },
  badgeText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  metricsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginBottom: 12 },
  metric: {},
  metricLabel: { fontSize: 12, color: SUB, marginBottom: 2 },
  metricValue: { fontSize: 15, fontWeight: '700', color: TEXT },

  visualWrap: {
    marginTop: 8,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#fff',
    minHeight: 120,
  },
  visualImage: { width: '100%', height: 200 },

  keywordGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  keywordChip: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: BORDER,
  },
  keywordChipDetected: { borderColor: ACCENT_GREEN, backgroundColor: '#E8F8F2' },
  keywordText: { fontSize: 14, fontWeight: '600', color: TEXT },
  keywordTextDetected: { color: ACCENT_GREEN_DARK },
  keywordStatus: { fontSize: 11, color: SUB, marginTop: 2 },

  riskBadge: {
    alignSelf: 'flex-start',
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: 8,
    marginBottom: 10,
  },
  riskBadgeText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  riskReason: { fontSize: 14, color: TEXT, marginBottom: 10, lineHeight: 20 },

  transcriptBox: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: BORDER,
    marginBottom: 12,
  },
  transcriptLabel: { fontSize: 12, fontWeight: '700', color: SUB, marginBottom: 6 },
  transcriptText: { fontSize: 13, color: TEXT, lineHeight: 20 },

  searchSection: { marginTop: 4 },
  searchItem: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: BORDER,
    marginTop: 8,
  },
  searchKeyword: { fontSize: 11, fontWeight: '700', color: ACCENT_GREEN_DARK, marginBottom: 2 },
  searchTitle: { fontSize: 13, fontWeight: '600', color: TEXT, marginBottom: 4 },
  searchContent: { fontSize: 12, color: SUB, lineHeight: 18 },

  actionsSection: { marginTop: 24, paddingTop: 20, borderTopWidth: 1, borderTopColor: BORDER },
  actionsSectionTitle: { fontSize: 15, fontWeight: '700', color: TEXT, marginBottom: 12 },
  actionsRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },

  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: ACCENT_GREEN,
  },
  actionLabel: { fontSize: 14, fontWeight: '700', color: ACCENT_GREEN },
});