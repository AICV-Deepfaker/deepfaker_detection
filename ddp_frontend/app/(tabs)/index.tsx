import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { Alert, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { setPendingImageUri, setPendingVideoUri } from '@/lib/pending-upload';

// 메인 액센트 색상 (#00CF90)
const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';

// 밝은 배경용 텍스트 색상
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { totalPoints, reportCount } = useAnalysis();

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

  const pickImage = async () => {
    const hasPermission = await requestMediaPermission();
    if (!hasPermission) return;

    // 일부 기기에서 "Can't load some Photos"가 나와도 OK 누른 뒤 보이는 사진 선택 가능
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: false,
      quality: 1,
      allowsMultipleSelection: false,
    });

    if (!result.canceled && result.assets[0]) {
      const uri = result.assets[0].uri;
      router.push(`/(tabs)/chatbot?imageUri=${encodeURIComponent(uri)}`);
    }
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

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}>
        {/* Green Header */}
        <View style={[styles.greenHeader, { paddingTop: insets.top + 8 }]}>
          <ThemedText style={styles.pointsText}>포인트 {totalPoints.toLocaleString()}</ThemedText>
          <View style={styles.headerRow}>
            <View style={styles.headerContent}>
              <ThemedText style={styles.headerTitle}>
                유명인 사칭{'\n'} 
                딥페이크 금융사기{'\n'}
                신고하고{'\n'}
                보상받으세요!
              </ThemedText>
              <ThemedText style={styles.reportCountText}>신고 접수 {reportCount}건</ThemedText>
            </View>
            <Image
              source={require('@/assets/images/ddp_logo.png')}
              style={styles.logoImage}
              contentFit="contain"
            />
          </View>
        </View>

        {/* White Content Area */}
        <View style={styles.whiteContentWrapper}>
          <View style={styles.whiteContent}>
          <TouchableOpacity
            style={styles.reportButton}
            activeOpacity={0.8}
            onPress={() => router.push('/fraud-report')}>
            <View style={styles.reportButtonContent}>
              <Image
                source={require('@/assets/images/alarm.png')}
                style={styles.reportButtonIcon}
                contentFit="contain"
              />
              <View style={styles.reportButtonTextWrap}>
                <ThemedText style={styles.reportButtonText}>딥페이크 금융사기 영상 신고</ThemedText>
                <ThemedText style={styles.reportButtonSubtext}>신고하고 보상받기</ThemedText>
              </View>
            </View>
          </TouchableOpacity>

        {/* Link Analysis Section */}
        <View style={styles.linkSection}>
          <View style={styles.linkIconWrapper}>
            <MaterialIcons name="link" size={48} color={ACCENT_GREEN} />
          </View>
          <ThemedText style={styles.linkSectionTitle}>링크로 바로 분석</ThemedText>
          <ThemedText style={styles.linkSectionSubtitle}>
            또는 소셜 미디어 앱에서 직접 공유
          </ThemedText>
          <TouchableOpacity
            style={styles.pasteButton}
            activeOpacity={0.8}
            onPress={() => router.push('/link-paste')}>
            <MaterialIcons name="description" size={20} color="#fff" />
            <ThemedText style={styles.pasteButtonText}>링크 붙여넣기</ThemedText>
            <MaterialIcons name="chevron-right" size={20} color="#fff" />
          </TouchableOpacity>
        </View>

        {/* Divider */}
        <ThemedText style={styles.dividerText}>또는 직접 업로드</ThemedText>

        {/* Upload Section */}
        <View style={styles.uploadSection}>
          <TouchableOpacity style={styles.uploadButton} activeOpacity={0.8} onPress={pickImage}>
            <View style={styles.uploadIconWrapper}>
              <MaterialIcons name="image" size={32} color={ACCENT_GREEN} />
            </View>
            <ThemedText style={styles.uploadButtonText}>이미지 업로드</ThemedText>
          </TouchableOpacity>

          <TouchableOpacity style={styles.uploadButton} activeOpacity={0.8} onPress={pickVideo}>
            <View style={styles.uploadIconWrapper}>
              <MaterialIcons name="videocam" size={32} color={ACCENT_GREEN} />
            </View>
            <ThemedText style={styles.uploadButtonText}>영상 업로드</ThemedText>
          </TouchableOpacity>
        </View>
        </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 24,
  },
  greenHeader: {
    backgroundColor: ACCENT_GREEN_DARK,
    paddingHorizontal: 20,
    paddingBottom: 28,
  },
  pointsText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 16,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerContent: {
    flex: 1,
  },
  headerTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 30,
    marginBottom: 8,
  },
  headerSubtitle: {
    color: 'rgba(255,255,255,0.95)',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  reportCountText: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 14,
  },
  logoImage: {
    width: 230,
    height: 230,
    marginRight: -40,
  },
  whiteContentWrapper: {
    flex: 1,
    marginTop: -20,
    borderRadius: 24,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  whiteContent: {
    flex: 1,
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 24,
  },
  linkSectionTitle: {
    color: TEXT_COLOR,
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 2,
    textAlign: 'center',
  },
  reportButton: {
    marginBottom: 20,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    backgroundColor: ACCENT_GREEN,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 14,
  },
  reportButtonContent: {
    alignItems: 'center',
    gap: 8,
  },
  reportButtonIcon: {
    width: 24,
    height: 24,
  },
  reportButtonTextWrap: {
    alignItems: 'center',
  },
  reportButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  reportButtonSubtext: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 13,
    marginTop: 2,
  },
  linkSection: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 28,
    alignItems: 'center',
    marginBottom: 28,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  linkIconWrapper: {
    marginBottom: 16,
  },
  linkSectionSubtitle: {
    color: SECONDARY_TEXT_COLOR,
    fontSize: 14,
    marginBottom: 20,
  },
  pasteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: ACCENT_GREEN,
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 14,
    width: '100%',
    gap: 10,
  },
  pasteButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  dividerText: {
    textAlign: 'center',
    fontSize: 15,
    marginBottom: 20,
    color: SECONDARY_TEXT_COLOR,
  },
  uploadSection: {
    flexDirection: 'row',
    gap: 16,
  },
  uploadButton: {
    flex: 1,
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    backgroundColor: '#fff',
  },
  uploadIconWrapper: {
    marginBottom: 12,
    padding: 16,
    backgroundColor: 'rgba(0, 207, 144, 0.15)',
    borderRadius: 16,
  },
  uploadButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: TEXT_COLOR,
  },
});
