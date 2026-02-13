import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import React, { useMemo } from 'react';
import { Alert, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { setPendingVideoUri } from '@/lib/pending-upload';

const MINT_CARD = '#D6F6E4';
const BLUE_CARD = '#D7ECFF';
const ACCENT = '#00CF90';
const TEXT = '#111';
const SUB = '#687076';

type QuickAction = {
  key: string;
  label: string;
  iconName: React.ComponentProps<typeof MaterialIcons>['name'];
  onPress: () => void;
};

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { totalPoints } = useAnalysis();

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
      router.push('/(tabs)/chatbot?pendingVideo=1');
    }
  };

  const quickActions: QuickAction[] = useMemo(
    () => [
      {
        key: 'report',
        label: '신고내역',
        iconName: 'wifi', // ✅ 임시 아이콘 (나중에 png 생기면 교체)
        onPress: () => router.push('/(tabs)/history'),
      },
      {
        key: 'upload',
        label: '업로드',
        iconName: 'mail-outline', // ✅ 임시 아이콘
        onPress: pickVideo, // 일단 업로드 = 영상 업로드로 연결
      },
      {
        key: 'result',
        label: '탐지결과',
        iconName: 'pie-chart-outline', // ✅ 임시 아이콘
        onPress: () => router.push('/(tabs)/history'),
      },
      {
        key: 'news',
        label: '피해뉴스',
        iconName: 'image-outline', // ✅ 임시 아이콘
        onPress: () => router.push('/(tabs)/chatbot'),
      },
    ],
    [],
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}>
        {/* Top: Points */}
        <View style={styles.topRow}>
          <ThemedText style={styles.pointsTitle}>
            내 포인트 {totalPoints.toLocaleString()}P
          </ThemedText>
        </View>

        {/* Quick Actions (원형 버튼 4개) */}
        <View style={styles.quickRow}>
          {quickActions.map((a) => (
            <TouchableOpacity key={a.key} style={styles.quickItem} activeOpacity={0.85} onPress={a.onPress}>
              <View style={styles.quickCircle}>
                <MaterialIcons name={a.iconName} size={26} color={ACCENT} />
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
            source={require('/Users/sienna/deepfaker_detection/ddp_frontend/assets/images/glass.png')}
            style={styles.bigCardImage}
            contentFit="contain"
          />
        </TouchableOpacity>

        {/* Blue Card: 신고하기 */}
        <TouchableOpacity
          activeOpacity={0.9}
          style={[styles.bigCard, { backgroundColor: BLUE_CARD }]}
          onPress={() => router.push('/fraud-report')}>
          <View style={styles.bigCardText}>
            <ThemedText style={styles.bigTitle}>신고하고 보상받으세요</ThemedText>
            <View style={styles.linkRowBlue}>
              <ThemedText style={styles.bigLinkBlue}>신고하기</ThemedText>
              <MaterialIcons name="chevron-right" size={18} color={'#3A7BD5'} />
            </View>
          </View>

          <Image
            source={require('/Users/sienna/deepfaker_detection/ddp_frontend/assets/images/siren.png')}
            style={styles.bigCardImage}
            contentFit="contain"
          />
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingHorizontal: 18 },

  topRow: { paddingTop: 8, paddingBottom: 14 },
  pointsTitle: { fontSize: 18, fontWeight: '700', color: TEXT },

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
});