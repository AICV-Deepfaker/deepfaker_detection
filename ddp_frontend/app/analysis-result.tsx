import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
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
import {
  predictWithFile,
  predictWithImageFile,
  type PredictResult,
  type PredictMode,
} from '@/lib/api';
import { takePendingImageUri, takePendingVideoUri } from '@/lib/pending-upload';

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
      {visualBase64 && (
        <View style={styles.visualWrap}>
          <Image
            source={{ uri: `data:image/png;base64,${visualBase64}` }}
            style={styles.visualImage}
            contentFit="contain"
          />
        </View>
      )}
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

export default function AnalysisResultScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{
    pendingImage?: string;
    pendingVideo?: string;
    mode?: string;
  }>();
  const mode = (params.mode === 'fast' ? 'fast' : 'deep') as PredictMode;
  const isEvidence = mode === 'fast';

  const { addToHistory } = useAnalysis();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictResult | null>(null);
  const viewShotRef = useRef<ViewShot>(null);

  const initialMediaRef = useRef<{ uri: string; type: 'image' | 'video' } | null>(null);
  if (initialMediaRef.current === null) {
    const img = takePendingImageUri();
    const vid = takePendingVideoUri();
    if (img) initialMediaRef.current = { uri: img, type: 'image' };
    else if (vid) initialMediaRef.current = { uri: vid, type: 'video' };
  }
  const mediaUri = initialMediaRef.current?.uri ?? null;
  const mediaType = initialMediaRef.current?.type ?? 'video';

  const runAnalysis = useCallback(async () => {
    if (!mediaUri) {
      setError('분석할 파일이 없습니다.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res =
        mediaType === 'image'
          ? await predictWithImageFile(mediaUri, mode)
          : await predictWithFile(mediaUri, mode);
      if (res.status === 'error') {
        setError(res.message ?? '분석 실패');
        setData(null);
      } else {
        setData(res);
        addToHistory(
          mediaType === 'image' ? '이미지 파일' : '영상 파일',
          formatResultText(res),
          res.result,
          res.visual_report
        );
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : '네트워크 오류';
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [mediaUri, mediaType, mode, addToHistory]);

  useEffect(() => {
    runAnalysis();
  }, []);

  const handleShare = useCallback(async () => {
    if (!data) return;
    const message = formatResultText(data);
    try {
      await Share.share({
        message,
        title: 'DDP 딥페이크 분석 결과',
      });
    } catch (_) {}
  }, [data]);

  const handleCopyLink = useCallback(async () => {
    if (!data) return;
    const text = formatResultText(data);
    await Clipboard.setStringAsync(text);
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
      const { uri } = await Print.printToFileAsync({
        html,
        baseUrl: '',
      });
      if (uri && (await Sharing.isAvailableAsync())) {
        await Sharing.shareAsync(uri, { mimeType: 'application/pdf' });
      }
    } catch (e) {
      Alert.alert('저장 실패', e instanceof Error ? e.message : 'PDF 저장에 실패했습니다.');
    }
  }, [data, isEvidence]);

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

        {/* 공통: 공유 / 저장 */}
        <View style={styles.actionsSection}>
          <ThemedText style={styles.actionsSectionTitle}>결과 공유 및 저장</ThemedText>
          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
              <MaterialIcons name="share" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>공유하기</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton} onPress={handleCopyLink}>
              <MaterialIcons name="link" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.actionLabel}>링크복사</ThemedText>
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
  return `
<!DOCTYPE html>
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
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
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
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: TEXT,
    marginBottom: 10,
  },
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

  metricsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
    marginBottom: 12,
  },
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
