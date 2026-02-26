import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Dimensions,
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
import { useAnalysis, POINTS_PER_REPORT, GIFT_THRESHOLD, getBadgeForPoints } from '@/contexts/analysis-context';
import { predictWithFile, predictWithVideoId, getMe, postAlert, type PredictMode, type PredictResult, type SttSearchResult, type AlertResponse } from '@/lib/api';
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

const SCREEN_WIDTH = Dimensions.get('window').width;

function VisualImage({ url }: { url: string }) {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [imgHeight, setImgHeight] = useState(320);

  const containerWidth = SCREEN_WIDTH - 64; // 카드 padding 제외

console.log('현재 포인트:', points?.activePoints);

  return (
    <View style={[styles.visualWrap, { height: status === 'ok' ? imgHeight : 160 }]}>
      {/* Image는 항상 실제 크기로 렌더링 — opacity로 가시성 제어
          height:0 이면 expo-image가 onLoad/onError를 발화하지 않으므로 absoluteFillObject 사용 */}
      <Image
        source={{ uri: url }}
        style={[StyleSheet.absoluteFillObject, { opacity: status === 'ok' ? 1 : 0 }]}
        contentFit="contain"
        onLoad={(e) => {
          const { width, height } = e.source;
          if (width && height) {
            const ratio = height / width;
            setImgHeight(Math.min(containerWidth * ratio, 700));
          }
          setStatus('ok');
        }}
        onError={() => setStatus('error')}
      />
      {status === 'loading' && (
        <View style={styles.visualPlaceholder}>
          <ActivityIndicator size="large" color={ACCENT_GREEN} />
          <ThemedText style={styles.visualPlaceholderText}>시각화 이미지 로딩 중...</ThemedText>
        </View>
      )}
      {status === 'error' && (
        <View style={styles.visualPlaceholder}>
          <MaterialIcons name="broken-image" size={40} color={SUB} />
          <ThemedText style={styles.visualPlaceholderText}>이미지를 불러올 수 없습니다</ThemedText>
          <ThemedText style={styles.visualErrorUrl} numberOfLines={2}>{url}</ThemedText>
        </View>
      )}
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

function SectionCard({
  title,
  result,
  probability,
  visualUrl,
  children,
}: {
  title: string;
  result?: 'FAKE' | 'REAL' | 'UNKNOWN';
  probability?: number;
  visualUrl?: string;
  children?: React.ReactNode;
}) {
  const hasContent = visualUrl != null || React.Children.count(children) > 0;
  const [expanded, setExpanded] = useState(false);
  const percent =
              probability != null
                ? (result === 'FAKE'
                    ? probability * 100
                    : result === 'REAL'
                      ? (1 - probability) * 100
                      : probability * 100)
                : null;

  return (
    <View style={styles.sectionCard}>
      {/* 항상 보이는 헤더 */}
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => hasContent && setExpanded(!expanded)}
        activeOpacity={hasContent ? 0.7 : 1}
      >
        <View style={styles.sectionHeaderLeft}>
          <ThemedText style={styles.sectionTitle}>{title}</ThemedText>
          {result != null && result !== 'UNKNOWN' && <ResultBadge result={result} />}
        </View>
        <View style={styles.sectionHeaderRight}>
          {percent != null && (
            <ThemedText style={styles.metricValueInline}>
              {percent.toFixed(1)}%
            </ThemedText>
          )}
          {hasContent && (
            <MaterialIcons
              name={expanded ? 'keyboard-arrow-up' : 'keyboard-arrow-down'}
              size={22}
              color={SUB}
            />
          )}
        </View>
      </TouchableOpacity>

      {/* 펼쳐질 때만 보이는 내용 */}
      {expanded && hasContent && (
        <View style={styles.sectionContent}>
          {probability != null && (
            <View style={styles.metricsRow}>
              <View style={styles.metric}>
                <ThemedText style={styles.metricLabel}>확률</ThemedText>
                {percent != null && (
                  <ThemedText style={styles.metricValue}>{percent.toFixed(2)}%</ThemedText>
                )}
              </View>
            </View>
          )}
          {visualUrl ? <VisualImage url={visualUrl} /> : null}
          {children}
        </View>
      )}
    </View>
  );
}

function SttKeywordsCard({ keywords }: { keywords: { keyword: string; detected: boolean }[] }) {
  const [expanded, setExpanded] = useState(false);
  const list = keywords.length ? keywords : STT_KEYWORDS.map((k) => ({ keyword: k, detected: false }));
  const detectedCount = list.filter(k => k.detected).length;

  return (
    <View style={styles.sectionCard}>
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.sectionHeaderLeft}>
          <ThemedText style={styles.sectionTitle}>STT 키워드</ThemedText>
          {detectedCount > 0 && (
            <View style={[styles.badge, styles.badgeFake]}>
              <ThemedText style={styles.badgeText}>{detectedCount}개 감지</ThemedText>
            </View>
          )}
        </View>
        <MaterialIcons
          name={expanded ? 'keyboard-arrow-up' : 'keyboard-arrow-down'}
          size={22}
          color={SUB}
        />
      </TouchableOpacity>

      {expanded && (
        <View style={styles.sectionContent}>
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
      )}
    </View>
  );
}

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
  const [expanded, setExpanded] = useState(false);
  if (!riskLevel && !transcript) return null;

  const color = RISK_COLOR[riskLevel ?? 'none'] ?? '#90A4AE';
  const label = RISK_LABEL[riskLevel ?? 'none'] ?? riskLevel;

  return (
    <View style={styles.sectionCard}>
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.sectionHeaderLeft}>
          <ThemedText style={styles.sectionTitle}>STT 사기 분석</ThemedText>
          {riskLevel && (
            <View style={[styles.riskBadgeInline, { backgroundColor: color }]}>
              <ThemedText style={styles.riskBadgeText}>{label?.toUpperCase()}</ThemedText>
            </View>
          )}
        </View>
        <MaterialIcons
          name={expanded ? 'keyboard-arrow-up' : 'keyboard-arrow-down'}
          size={22}
          color={SUB}
        />
      </TouchableOpacity>

      {expanded && (
        <View style={styles.sectionContent}>
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
      )}
    </View>
  );
}

export default function AnalysisResultScreen() {
  const insets = useSafeAreaInsets();

  const params = useLocalSearchParams<{ mode?: string; pendingVideo?: string; videoId?: string }>();
  const mode = (params.mode === 'fast' ? 'fast' : 'deep') as PredictMode;
  const videoId = params.videoId ?? null;
  const isEvidence = mode === 'fast';

  const { addToHistory, setPointsFromServer, totalPoints } = useAnalysis();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictResult | null>(null);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const [reported, setReported] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDone, setShowDone] = useState(false);

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

      // 판정은 wavelet 기준
      const freqResult = (res.frequency?.result as 'FAKE' | 'REAL' | undefined)
        ?? (res.result === 'UNKNOWN' ? undefined : res.result as 'FAKE' | 'REAL' | undefined);

      const newId = addToHistory(
        '영상 파일',
        formatResultText(res),
        freqResult,
        res.frequency?.visual_url,  // wavelet 이미지 URL
        res.result_id,
      );

      setHistoryId(newId);
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

  const handleReport = useCallback(async () => {
    if (!data?.result_id) return;
    const key = `reported:${historyId}`;
    const already = await AsyncStorage.getItem(key);
    if (already === '1') { setReported(true); return; }

    try {
      const alertRes: AlertResponse = await postAlert({ result_id: data.result_id });
      await AsyncStorage.setItem(key, '1');
      setReported(true);

      // alert 응답에 포함된 포인트로 바로 업데이트
      if (alertRes.total_points != null) {
        setPointsFromServer({ activePoints: alertRes.total_points, totalPoints: alertRes.total_points });
      } else {
        // fallback: /me 재조회
        const me = await getMe();
        setPointsFromServer({ activePoints: me.active_points, totalPoints: me.total_points ?? me.active_points });
      }
      setShowDone(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '신고 중 오류가 발생했습니다.';
      if (msg === 'already reported') {
        // 서버에선 이미 신고됨 → 로컬도 신고 완료로 표시
        await AsyncStorage.setItem(key, '1');
        setReported(true);
      } else {
        Alert.alert('신고 실패', msg);
      }
    }
  }, [data?.result_id, historyId, setPointsFromServer]);

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

  // fast: wavelet 기준 / deep: unite 기준
  const freqResult = data.frequency?.result ?? (data.result === 'UNKNOWN' ? undefined : data.result);
  const isFake = freqResult === 'FAKE';
  // probability는 REAL 확률 기준: FAKE면 fake% = (1-prob)*100, REAL이면 real% = prob*100
  // deep mode에서는 data.frequency가 없으므로 data.unite?.probability로 fallback
  const displayProb = data.frequency?.probability ?? data.unite?.probability;
  const displayPercent = displayProb != null
    ? Math.round(isFake ? displayProb * 100 : (1 - displayProb) * 100)
    : null;
  const analysisLabel = isEvidence ? '주파수 분석 기준' : 'UNITE 분석 기준';

  const { current: currentBadge } = getBadgeForPoints((totalPoints ?? 0) + (reported ? 0 : POINTS_PER_REPORT));

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
        {/* 최종 판정 (wavelet 기준) */}
        {freqResult != null && (
          <View style={styles.verdictCard}>
            <ThemedText style={styles.verdictTitle}>최종 판정</ThemedText>
            <View style={styles.verdictRow}>
              <View style={[styles.verdictPill, isFake ? styles.pillFake : styles.pillReal]}>
                <MaterialIcons name={isFake ? 'warning' : 'check-circle'} size={18} color="#fff" />
                <ThemedText style={styles.verdictPillText}>{isFake ? 'FAKE' : 'REAL'}</ThemedText>
              </View>
              {displayPercent != null && (
                <ThemedText style={styles.verdictPercent}>{displayPercent}%</ThemedText>
              )}
            </View>
            {displayPercent != null && (
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, {
                  width: `${displayPercent}%`,
                  backgroundColor: isFake ? '#FF6B6B' : '#7ED957',
                }]} />
              </View>
            )}
            <ThemedText style={styles.verdictCaption}>
              {isFake ? `딥페이크/사기 의심 확률 (${analysisLabel})` : `정상 콘텐츠로 판단될 확률 (${analysisLabel})`}
            </ThemedText>
          </View>
        )}

        <ViewShot ref={viewShotRef} options={{ format: 'png', quality: 1 }} style={styles.shotWrap}>
          {isEvidence ? (
            <>
              <SectionCard
                title="주파수 분석"
                result={data.frequency?.result}
                probability={data.frequency?.probability}
                visualUrl={data.frequency?.visual_url}
              />
              <SectionCard
                title="rPPG 분석"
                visualUrl={data.rppg?.visual_url}
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
              result={data.unite?.result}
              probability={data.unite?.probability}
            />
          )}
        </ViewShot>

        {/* 신고하기 버튼 */}
        <View style={styles.reportWrap}>
          {reported ? (
            <View style={[styles.reportButton, styles.reportDone]}>
              <MaterialIcons name="check-circle" size={20} color="#fff" />
              <ThemedText style={styles.reportButtonText}>신고 완료</ThemedText>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.reportButton}
              activeOpacity={0.85}
              onPress={() => setShowConfirm(true)}
            >
              <MaterialIcons name="report" size={20} color="#fff" />
              <ThemedText style={styles.reportButtonText}>신고하기</ThemedText>
            </TouchableOpacity>
          )}
        </View>

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

      {/* 신고 확인 모달 */}
      {showConfirm && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <MaterialIcons name="warning-amber" size={34} color="#E53935" style={{ alignSelf: 'center', marginBottom: 14 }} />
            <ThemedText style={styles.modalTitle}>신고 확인</ThemedText>
            <ThemedText style={styles.modalText}>이 콘텐츠를 신고하시겠습니까?</ThemedText>
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.modalCancel} onPress={() => setShowConfirm(false)}>
                <ThemedText style={styles.modalCancelText}>아니오</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalConfirm} onPress={async () => {
                setShowConfirm(false);
                await handleReport();
              }}>
                <ThemedText style={styles.modalConfirmText}>신고하기</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* 신고 완료 모달 */}
      {showDone && (
        <View style={styles.successOverlay}>
          <View style={styles.successCard}>
            <ThemedText style={{ fontSize: 20, marginBottom: 4 }}>🎉🎉🎉</ThemedText>
            <MaterialIcons name="check-circle" size={40} color={ACCENT_GREEN} style={{ marginBottom: 12 }} />
            <ThemedText style={styles.successTitle}>신고 완료</ThemedText>
            <ThemedText style={styles.successPoints}>+{POINTS_PER_REPORT.toLocaleString()} 포인트가 추가되었습니다!</ThemedText>
            <ThemedText style={styles.successSubtext}>
              {GIFT_THRESHOLD.toLocaleString()} 포인트를 모으면 스타벅스 아메리카노 기프티콘을 받을 수 있어요.
            </ThemedText>
            <View style={styles.successBadgeRow}>
              <ThemedText style={{ fontSize: 20 }}>{currentBadge.icon}</ThemedText>
              <ThemedText style={styles.successBadgeName}>{currentBadge.name}</ThemedText>
            </View>
            <TouchableOpacity style={styles.successButton} onPress={() => setShowDone(false)} activeOpacity={0.85}>
              <ThemedText style={styles.successButtonText}>확인</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

function formatResultText(data: PredictResult): string {
  const freqResult = data.frequency?.result ?? data.result ?? '-';
  const freqProb = data.frequency?.probability ?? data.average_fake_prob;
  let displayProb = '-';
  if (freqProb != null) {
    // probability는 REAL 확률: FAKE이면 fake% = (1-p)*100, REAL이면 real% = p*100
    const isFk = freqResult === 'FAKE';
    displayProb = (isFk ? (1 - freqProb) * 100 : freqProb * 100).toFixed(2);
  }
  return `[DDP 분석 결과]\n판정: ${freqResult}\n딥페이크 확률: ${displayProb}%`;
}

function buildResultHtml(data: PredictResult, isEvidence: boolean): string {
  const r = data.result ?? '-';
  const p = data.average_fake_prob != null ? (data.average_fake_prob * 100).toFixed(2) : '-';
  const modeLabel = isEvidence ? '증거수집모드' : '정밀탐지모드';

  const freqImg = data.frequency?.visual_url
    ? `<img src="${data.frequency.visual_url}" style="max-width:100%;height:auto;" />`
    : '';
  const rppgImg = data.rppg?.visual_url
    ? `<img src="${data.rppg.visual_url}" style="max-width:100%;height:auto;" />`
    : '';

  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>DDP 분석 결과</title></head>
<body style="font-family:sans-serif;padding:20px;color:#111;">
  <h2>DDP 딥페이크 분석 결과 (${modeLabel})</h2>
  <p><strong>판정:</strong> ${r} &nbsp; <strong>확률:</strong> ${p}%</p>
  ${freqImg}${rppgImg}
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
    overflow: 'hidden',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: BORDER,
  },

  // 접기/펼치기 헤더
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  sectionHeaderLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginRight: 8,
  },
  sectionHeaderRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  sectionContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: BORDER,
    paddingTop: 12,
  },

  sectionTitle: { fontSize: 16, fontWeight: '700', color: TEXT },
  metricValueInline: { fontSize: 14, fontWeight: '700', color: TEXT },

  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  badgeFake: { backgroundColor: FAKE_RED },
  badgeReal: { backgroundColor: REAL_GREEN },
  badgeText: { color: '#fff', fontWeight: '700', fontSize: 13 },

  metricsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginBottom: 12 },
  metric: {},
  metricLabel: { fontSize: 12, color: SUB, marginBottom: 2 },
  metricValue: { fontSize: 15, fontWeight: '700', color: TEXT },

  visualWrap: {
    marginTop: 8,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#F4F6F8',
    borderWidth: 1,
    borderColor: BORDER,
  },
  visualPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 32,
    gap: 10,
  },
  visualPlaceholderText: {
    fontSize: 13,
    color: SUB,
  },
  visualErrorUrl: {
    fontSize: 10,
    color: SUB,
    textAlign: 'center',
    paddingHorizontal: 12,
    opacity: 0.6,
  },

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
  riskBadgeInline: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 8,
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

  actionsSection: { marginTop: 16, paddingTop: 20, borderTopWidth: 1, borderTopColor: BORDER },
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

  // 최종 판정 카드
  verdictCard: {
    backgroundColor: CARD_BG,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: BORDER,
  },
  verdictTitle: { fontSize: 16, fontWeight: '700', color: TEXT, marginBottom: 12 },
  verdictRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  verdictPill: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 14, paddingVertical: 10, borderRadius: 999,
  },
  pillFake: { backgroundColor: '#FF2D2D' },
  pillReal: { backgroundColor: REAL_GREEN },
  verdictPillText: { color: '#fff', fontSize: 20, fontWeight: '900', letterSpacing: 0.5 },
  verdictPercent: { fontSize: 28, fontWeight: '900', color: TEXT },
  progressTrack: { height: 16, borderRadius: 999, backgroundColor: 'rgba(0,0,0,0.12)', overflow: 'hidden', marginBottom: 10 },
  progressFill: { height: '100%', borderRadius: 999 },
  verdictCaption: { color: SUB, fontSize: 13 },

  // 신고 버튼
  reportWrap: { marginBottom: 16 },
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

  // 모달
  modalOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'center', alignItems: 'center', padding: 24,
  },
  modalCard: {
    width: '100%', backgroundColor: '#fff', borderRadius: 20, padding: 24,
    borderWidth: 1, borderColor: 'rgba(0,0,0,0.06)',
  },
  modalTitle: { fontSize: 18, fontWeight: '800', textAlign: 'center', color: '#111', marginBottom: 8 },
  modalText: { fontSize: 14, textAlign: 'center', color: '#687076', marginBottom: 24 },
  modalButtons: { flexDirection: 'row', gap: 12 },
  modalCancel: {
    flex: 1, paddingVertical: 14, borderRadius: 14, borderWidth: 1,
    borderColor: '#E0E0E0', alignItems: 'center',
  },
  modalCancelText: { fontWeight: '700', color: '#687076' },
  modalConfirm: { flex: 1, paddingVertical: 14, borderRadius: 14, backgroundColor: ACCENT_GREEN, alignItems: 'center' },
  modalConfirmText: { fontWeight: '800', color: '#fff' },

  successOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'center', alignItems: 'center', padding: 24,
  },
  successCard: {
    width: '100%', maxWidth: 340, backgroundColor: '#fff', borderRadius: 24,
    padding: 24, alignItems: 'center', borderWidth: 1, borderColor: 'rgba(0,0,0,0.06)',
  },
  successTitle: { fontSize: 20, fontWeight: '800', color: TEXT, marginBottom: 10 },
  successPoints: { fontSize: 16, fontWeight: '800', color: ACCENT_GREEN_DARK, marginBottom: 8 },
  successSubtext: { fontSize: 13, color: SUB, textAlign: 'center', lineHeight: 18, marginBottom: 14 },
  successBadgeRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: 'rgba(0,207,144,0.10)', paddingVertical: 10, paddingHorizontal: 14,
    borderRadius: 12, marginBottom: 18,
  },
  successBadgeName: { fontSize: 14, fontWeight: '800', color: ACCENT_GREEN_DARK },
  successButton: { width: '100%', backgroundColor: ACCENT_GREEN, paddingVertical: 14, borderRadius: 14, alignItems: 'center' },
  successButtonText: { fontSize: 16, fontWeight: '800', color: '#fff' },
});