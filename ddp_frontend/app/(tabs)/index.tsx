import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import React, { useEffect, useMemo, useCallback, useState } from 'react';
import { Alert, ScrollView, StyleSheet, TouchableOpacity, View, Modal, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { getAuth } from '@/lib/auth-storage';
import { setPendingVideoUri } from '@/lib/pending-upload';

const MINT_CARD = '#D6F6E4';
const BLUE_CARD = '#D7ECFF';
const ACCENT = '#00CF90';
const TEXT = '#111';
const SUB = '#687076';
const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

type QuickAction = {
  key: string;
  label: string;
  icon: number;
  onPress: () => void;
};

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { totalPoints } = useAnalysis();
  const [nickname, setNickname] = React.useState<string | null>(null);
  const { history } = useAnalysis();


  useEffect(() => {
    getAuth().then((auth) => {
      if (!auth) router.replace('/login');
      else setNickname(auth.nickname ?? null);
    });
  }, []);

  const requestMediaPermission = async () => {
    const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!granted) {
      Alert.alert(
        '권한 필요',
        '갤러리에서 이미지와 영상을 선택하려면 권한이 필요합니다. 설정에서 권한을 허용해주세요.',
      );
      return false;
    }
    return true;
  };

  const pickVideo = async () => {
    const hasPermission = await requestMediaPermission();
    if (!hasPermission) return;

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['videos'],
      allowsEditing: false,
      quality: 1,
      allowsMultipleSelection: false,
    });

    if (!result.canceled && result.assets[0]) {
      const uri = result.assets[0].uri;
      setPendingVideoUri(uri);
      router.push('/link-paste');
    }
  };

  const quickActions: QuickAction[] = useMemo(
    () => [
      {
        key: 'report',
        label: '신고내역',
        icon: require('@/assets/images/home_list.png'),
        onPress: () => router.push('/(tabs)/report'),
      },
      {
        key: 'upload',
        label: '업로드',
        icon: require('@/assets/images/home_upload.png'),
        onPress: pickVideo,
      },
      {
        key: 'result',
        label: '탐지결과',
        icon: require('@/assets/images/home_result.png'),
        onPress: () => router.push('/(tabs)/history'),
      },
      {
        key: 'news',
        label: '피해뉴스',
        icon: require('@/assets/images/home_news.png'),
        onPress: () => router.push('/news' as const),
      },
    ],
    [],
  );

  const [infoOpen, setInfoOpen] = useState(false);

  const InfoModal = ({
    visible,
    onClose,
  }: {
    visible: boolean;
    onClose: () => void;
  }) => {
    return (
      <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
        <View style={styles.modalOverlay}>
          <Pressable style={styles.modalBackdrop} onPress={onClose} />
          <View style={styles.modalCard}>
            <View style={styles.modalIconWrap}>
              <MaterialIcons name="info-outline" size={26} color={ACCENT_GREEN} />
            </View>

            <ThemedText style={styles.modalTitle}>분석 기록이 필요해요</ThemedText>
            <ThemedText style={styles.modalDesc}>
              탐지 후 분석 기록이 있어야 신고할 수 있어요.{'\n'}
              먼저 링크/영상으로 분석을 진행해 주세요.
            </ThemedText>

            <TouchableOpacity style={styles.modalBtnPrimary} onPress={onClose} activeOpacity={0.85}>
              <ThemedText style={styles.modalBtnPrimaryText}>확인</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    );
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}>
        {/* 인사말 + 포인트 + 로고 */}
        <View style={styles.topRow}>
          <View style={styles.topRowLeft}>
            <ThemedText style={styles.greeting}>
              {nickname ?? '회원'}님,{'\n'}딥페이크 금융사기{'\n'}신고하고 보상받으세요!
            </ThemedText>
            <ThemedText style={styles.pointsTitle}>
              내 포인트 {totalPoints.toLocaleString()}P
            </ThemedText>
          </View>
          <Image
            source={require('@/assets/images/ddp_logo.gif')}
            style={styles.topRowLogo}
            contentFit="contain"
            autoplay
          />
        </View>

        {/* Quick Actions (원형 버튼 4개) */}
        <View style={styles.quickRow}>
          {quickActions.map((a) => (
            <TouchableOpacity key={a.key} style={styles.quickItem} activeOpacity={0.85} onPress={a.onPress}>
              <View style={styles.quickCircle}>
                <Image source={a.icon} style={styles.quickIcon} contentFit="contain" />
              </View>
              <ThemedText style={styles.quickLabel}>{a.label}</ThemedText>
            </TouchableOpacity>
          ))}
        </View>

        {/* Mint Card: 탐지해보기 */}
        <TouchableOpacity
          activeOpacity={0.9}
          style={[styles.bigCard, { backgroundColor: MINT_CARD }]}
          onPress={() => router.push('/link-paste')}>
          <View style={styles.bigCardText}>
            <ThemedText style={styles.bigTitle}>
              이 콘텐츠가{'\n'}사기로 의심돼요
            </ThemedText>
            <View style={styles.linkRow}>
              <ThemedText style={styles.bigLink}>탐지해보기</ThemedText>
              <MaterialIcons name="chevron-right" size={18} color={ACCENT} />
            </View>
          </View>

          <Image
            source={require('@/assets/images/glass.png')}
            style={styles.bigCardImage}
            contentFit="contain"
          />
        </TouchableOpacity>

        {/* Blue Card: 신고하기 */}
        <TouchableOpacity
          activeOpacity={0.9}
          style={[styles.bigCard, { backgroundColor: BLUE_CARD }]}
          onPress={() => {
              if (!history || history.length === 0) {
                setInfoOpen(true);
                return;
              }
              router.push('/(tabs)/history'); // 또는 router.push('/history') (너 프로젝트 구조에 맞게)
            }}
          >
          <View style={styles.bigCardText}>
            <ThemedText style={styles.bigTitle}>신고하고{'\n'}보상을 받아보세요</ThemedText>
            <View style={styles.linkRowBlue}>
              <ThemedText style={styles.bigLinkBlue}>신고하기</ThemedText>
              <MaterialIcons name="chevron-right" size={18} color={'#3A7BD5'} />
            </View>
          </View>

          <Image
            source={require('@/assets/images/siren.png')}
            style={[styles.bigCardImage, styles.sirenFlipped]}
            contentFit="contain"
          />
        </TouchableOpacity>

        {/* 뉴스 보기 칸 - 이미지 크게 */}
        <View style={styles.newsSection}>
          {/* <ThemedText style={styles.newsSectionTitle}>딥페이크 금융사기 피해 뉴스</ThemedText> */}
          <TouchableOpacity
            activeOpacity={0.95}
            style={styles.newsCard}
            onPress={() => router.push('/news' as const)}>
            <Image
              source={require('@/assets/images/news_image.png')}
              style={styles.newsThumbnail}
              contentFit="cover"
            />
            <View style={styles.newsCardFooter}>
              <ThemedText style={styles.newsCardHeadline}>DDP에서 딥페이크·금융사기 뉴스를 확인해보세요!</ThemedText>
              <ThemedText style={styles.newsCardSub}>
                무심코 믿은 영상, 딥페이크 피해자가 됩니다.
              </ThemedText>
              <View style={styles.newsCardRow}>
                <ThemedText style={styles.newsCardLink}>뉴스 보기</ThemedText>
                <MaterialIcons name="chevron-right" size={20} color={ACCENT} />
              </View>
            </View>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <InfoModal visible={infoOpen} onClose={() => setInfoOpen(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingHorizontal: 18 },

  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    paddingBottom: 14,
    paddingHorizontal: 10,
    gap: 12,
  },
  topRowLeft: { flex: 1 },
  greeting: {
    fontSize: 21,
    fontWeight: '700',
    color: TEXT,
    marginBottom: 6,
    lineHeight: 28,
  },
  pointsTitle: { fontSize: 16, fontWeight: '600', color: SUB },
  topRowLogo: { width: 90, height: 120 },

  quickRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingBottom: 18,
    gap: 10,
  },
  quickItem: { alignItems: 'center', flex: 1 },
  quickCircle: {
    width: 62,
    height: 62,
    borderRadius: 999,
    backgroundColor: '#F3F5F7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickIcon: { width: 40, height: 40 },
  quickLabel: { marginTop: 10, fontSize: 13, color: TEXT, fontWeight: '600' },

  bigCard: {
    borderRadius: 18,
    padding: 18,
    minHeight: 145,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
  },
  bigCardText: { flex: 1, paddingRight: 10 },
  bigTitle: { fontSize: 22, fontWeight: '800', color: TEXT, lineHeight: 30 },

  linkRow: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 4 },
  bigLink: { fontSize: 16, fontWeight: '700', color: ACCENT },

  linkRowBlue: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 4 },
  bigLinkBlue: { fontSize: 16, fontWeight: '700', color: '#3A7BD5' },

  bigCardImage: { width: 110, height: 110 },
  sirenFlipped: {
    width: 75,
    height: 75,
    marginRight: 20,
    transform: [{ scaleX: -1 }],
    marginBottom: -20
  },
  newsSection: {
    marginBottom: 14,
  },
  newsSectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: TEXT,
    marginBottom: 12,
  },
  newsCard: {
    borderRadius: 18,
    overflow: 'hidden',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  newsThumbnail: {
    width: '100%',
    height: 220,
    backgroundColor: '#E8E8E8',
  },
  newsCardFooter: {
    padding: 16,
    paddingTop: 14,
  },
  newsCardHeadline: {
    fontSize: 16,
    fontWeight: '700',
    color: TEXT,
    marginBottom: 6,
  },
  newsCardSub: {
    fontSize: 14,
    color: SUB,
    lineHeight: 20,
    marginBottom: 12,
  },
  newsCardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  newsCardLink: {
    fontSize: 15,
    fontWeight: '700',
    color: ACCENT,
  },
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
  modalBackdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  modalCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 22,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  modalIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(0, 207, 144, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 12,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: TEXT_COLOR,
    textAlign: 'center',
    marginBottom: 8,
  },
  modalDesc: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 16,
  },
  modalBtnPrimary: {
    backgroundColor: ACCENT_GREEN,
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
  modalBtnPrimaryText: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 15,
  },
});