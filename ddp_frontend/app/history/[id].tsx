import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Image } from 'expo-image';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import React, { useCallback, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis, getBadgeForPoints, POINTS_PER_REPORT, GIFT_THRESHOLD } from '@/contexts/analysis-context';
import { getMe, postAlert } from '@/lib/api';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';
const DANGER = '#E53935';

const extractFakeProbPercent = (text?: string) => {
  if (!text) return null;
  const m = text.match(/딥페이크\s*확률\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%/);
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
  const t = item?.contentType || item?.inputType || item?.sourceType || item?.type || item?.kind || '';
  const s = String(t).toLowerCase();
  if (s.includes('link') || s.includes('url')) return '링크';
  if (s.includes('video') || s.includes('mp4') || s.includes('mov')) return '영상 파일';
  if (s.includes('image') || s.includes('jpg') || s.includes('png') || s.includes('jpeg'))
    return '이미지 파일';

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

  const { history, totalPoints, setPointsFromServer } = useAnalysis();
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDone, setShowDone] = useState(false);
  const [reported, setReported] = useState(false);

  const item = useMemo(() => history.find((h) => h.id === id), [history, id]);

  const isFake = item?.resultType === 'FAKE';
  const percent = extractFakeProbPercent(item?.result) ?? 0;

  const storageKey = id ? `reported:${id}` : '';

  // ✅ 신고 이후 포인트 반영된 등급을 보여주고 싶어서 +POINTS_PER_REPORT 기준으로 계산
  const { current: currentBadge } = getBadgeForPoints((totalPoints ?? 0) + (reported ? 0 : POINTS_PER_REPORT));

  const onConfirmReport = useCallback(async () => {
    if (!id) return;

    const resultId = item?.resultId;
    if (resultId == null) {
      // result_id 없으면 신고 불가
      setShowDone(false);
      // 여기 Alert 쓰고 싶으면 import { Alert } from 'react-native';
      // Alert.alert('신고 불가', 'result_id가 없어 신고할 수 없습니다. 다시 분석 후 시도해주세요.');
      return;
    }

    // (선택) 로컬 중복 클릭 방지용 - 원칙 위반 아님
    const key = `reported:${id}`;
    const already = await AsyncStorage.getItem(key);
    if (already === '1') {
      setReported(true);
      return;
    }

    // ✅ 원칙 2: 신고는 /alerts POST로만
    await postAlert({ result_id: resultId });

    // 로컬 표시만 (서버 중복방지는 백엔드에서 409 등으로 처리하는 게 베스트)
    await AsyncStorage.setItem(key, '1');
    setReported(true);

    // ✅ 원칙 1: 포인트는 로컬에서 더하지 않음
    // 신고 후 서버 /me를 다시 받아서 최신 포인트로 갱신
    const me = await getMe();
    setPointsFromServer({
      activePoints: me.active_points,
      totalPoints: me.total_points ?? me.active_points,
    });

    setShowDone(true);
  }, [id, item?.resultId, setPointsFromServer]);

  useFocusEffect(
    useCallback(() => {
      if (!storageKey) return;

      (async () => {
        const v = await AsyncStorage.getItem(storageKey);
        setReported(v === '1');
      })();
    }, [storageKey]),
  );

  if (!item) {
    return (
      <View style={styles.container}>
        <View style={styles.center}>
          <ThemedText style={{ color: SECONDARY_TEXT_COLOR }}>해당 히스토리를 찾을 수 없습니다.</ThemedText>
        </View>
      </View>
    );
  }

  const contentLabel = getContentLabel(item);

  return (
    <View style={styles.container}>
        {/* ✅ Header */}
        <View style={[styles.header, { paddingTop: insets.top }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.headerBack} activeOpacity={0.8}>
            <MaterialIcons name="arrow-back" size={24} color={TEXT_COLOR} />
          </TouchableOpacity>

          <ThemedText style={styles.headerTitle}>분석 대시보드</ThemedText>
          <View style={styles.headerRightSpace} />
        </View>
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
              <MaterialIcons name={isFake ? 'warning' : 'check-circle'} size={18} color="#fff" />
              <ThemedText style={styles.pillText}>{isFake ? 'FAKE' : 'REAL'}</ThemedText>
            </View>

            <ThemedText style={styles.percentBig}>{Math.round(percent)}%</ThemedText>
          </View>

          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${Math.round(percent)}%`,
                  backgroundColor: isFake ? '#FF6B6B' : '#7ED957',
                },
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
              source={{ uri: item.visualReport }}
              style={styles.fullReportImage}
              contentFit="contain"
              cachePolicy="memory-disk"
            />
          </View>
        ) : null}

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
              onPress={() => setShowConfirm(true)}
            >
              <MaterialIcons name="report" size={20} color="#fff" />
              <ThemedText style={styles.reportButtonText}>신고하기</ThemedText>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>

      {/* ✅ Confirm Modal */}
      {showConfirm && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalIconWrap}>
              <MaterialIcons name="warning-amber" size={34} color={DANGER} />
            </View>

            <ThemedText style={styles.modalTitle}>신고 확인</ThemedText>
            <ThemedText style={styles.modalText}>이 콘텐츠를 신고하시겠습니까?</ThemedText>

            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.modalCancel} onPress={() => setShowConfirm(false)}>
                <ThemedText style={styles.modalCancelText}>아니오</ThemedText>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.modalConfirm}
                onPress={async () => {
                  setShowConfirm(false);
                  await onConfirmReport();
                }}
              >
                <ThemedText style={styles.modalConfirmText}>신고하기</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* ✅ Done Modal (요청한 UI로 업그레이드) */}
      {showDone && (
        <View style={styles.successOverlay}>
          <View style={styles.successCard}>
            {/* 폭죽(이미지 없으니 이모지 기본) */}
            <View style={styles.confettiWrap}>
              <ThemedText style={styles.confettiEmoji}>🎉🎉🎉</ThemedText>
            </View>

            <View style={styles.successCheckWrap}>
              <MaterialIcons name="check-circle" size={40} color={ACCENT_GREEN} />
            </View>

            <ThemedText style={styles.successTitle}>신고 완료</ThemedText>

            <ThemedText style={styles.successPoints}>
              +{POINTS_PER_REPORT.toLocaleString()} 포인트가 추가되었습니다!
            </ThemedText>

            <ThemedText style={styles.successSubtext}>
              {GIFT_THRESHOLD.toLocaleString()} 포인트를 모으면 스타벅스 아메리카노 기프티콘을 받을 수 있어요.
            </ThemedText>

            {/* 뱃지/등급 */}
            <View style={styles.successBadgeRow}>
              <ThemedText style={styles.successBadgeEmoji}>{currentBadge.icon}</ThemedText>
              <ThemedText style={styles.successBadgeName}>{currentBadge.name}</ThemedText>
            </View>

            <TouchableOpacity
              style={styles.successButton}
              onPress={() => setShowDone(false)}
              activeOpacity={0.85}
            >
              <ThemedText style={styles.successButtonText}>확인</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      )}
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
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 12,
    backgroundColor: '#F5F5F5',
  },

  headerBack: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },

  headerTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: 16,
    fontWeight: '800',
    color: TEXT_COLOR,
  },

  headerRightSpace: {
    width: 40,
    height: 40,
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

  // ===== 기존 confirm modal =====
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalCard: {
    width: '100%',
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  modalIconWrap: {
    alignItems: 'center',
    marginBottom: 14,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '800',
    textAlign: 'center',
    color: '#111',
    marginBottom: 8,
  },
  modalText: {
    fontSize: 14,
    textAlign: 'center',
    color: '#687076',
    marginBottom: 24,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  modalCancel: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    alignItems: 'center',
  },
  modalCancelText: {
    fontWeight: '700',
    color: '#687076',
  },
  modalConfirm: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 14,
    backgroundColor: ACCENT_GREEN,
    alignItems: 'center',
  },
  modalConfirmText: {
    fontWeight: '800',
    color: '#fff',
  },

  // ===== ✅ 신고 완료(새 UI) =====
  successOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  successCard: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  confettiWrap: { width: '100%', alignItems: 'center', marginBottom: 4 },
  confettiEmoji: { fontSize: 20 },

  successCheckWrap: { marginTop: 6, paddingVertical: 2, marginBottom: 12 },

  successTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: TEXT_COLOR,
    marginBottom: 10,
  },
  successPoints: {
    fontSize: 16,
    fontWeight: '800',
    color: ACCENT_GREEN_DARK,
    marginBottom: 8,
  },
  successSubtext: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 14,
  },
  successBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(0, 207, 144, 0.10)',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 12,
    marginBottom: 18,
  },
  successBadgeEmoji: { fontSize: 20 },
  successBadgeName: {
    fontSize: 14,
    fontWeight: '800',
    color: ACCENT_GREEN_DARK,
  },
  successButton: {
    width: '100%',
    backgroundColor: ACCENT_GREEN,
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
  successButtonText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#fff',
  },
});