import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { linkVideo, uploadVideo } from '@/lib/api';
import {
  peekPendingVideoUri,
  setPendingVideoUri,
} from '@/lib/pending-upload';
import { withAuth } from '@/lib/with-auth';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

type PlatformId = 'twitter' | 'youtube' | 'instagram' | 'facebook' | 'tiktok' | 'direct';

const PLATFORM_ICONS: Record<PlatformId, number> = {
  twitter: require('@/assets/images/twitter.png'),
  youtube: require('@/assets/images/youtube.png'),
  instagram: require('@/assets/images/instagram.png'),
  facebook: require('@/assets/images/facebook.png'),
  tiktok: require('@/assets/images/tiktok.png'),
  direct: require('@/assets/images/link.png'),
};

const PLATFORMS: { id: PlatformId; label: string }[] = [
  { id: 'twitter', label: 'Twitter/X' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'direct', label: '직접 링크' },
];

function detectPlatformFromUrl(url: string): PlatformId | null {
  const lower = url.toLowerCase().trim();
  if (!lower) return null;
  if (lower.includes('youtube.com') || lower.includes('youtube')) return 'youtube';
  if (lower.includes('instagram.com')) return 'instagram';
  if (lower.includes('twitter.com') || lower.includes('x.com')) return 'twitter';
  if (lower.includes('tiktok.com')) return 'tiktok';
  if (lower.includes('facebook.com') || lower.includes('fb.com') || lower.includes('fb.watch'))
    return 'facebook';
  if (lower.startsWith('http://') || lower.startsWith('https://')) return 'direct';
  return null;
}

type UploadedFile = { type: 'video'; uri: string };
type LinkUploadStatus = 'idle' | 'uploading' | 'done' | 'error';

export default function LinkPasteScreen() {
  const insets = useSafeAreaInsets();
  const [url, setUrl] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformId | null>(null);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [videoUploading, setVideoUploading] = useState(false);
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null);
  const [showModeButtons, setShowModeButtons] = useState(false);
  const [linkUploadStatus, setLinkUploadStatus] = useState<LinkUploadStatus>('idle');
  const [linkVideoId, setLinkVideoId] = useState<string | null>(null);
  const [showLinkModeButtons, setShowLinkModeButtons] = useState(false);
  const [submittedUrl, setSubmittedUrl] = useState('');
  const linkDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const canAnalyze = Boolean(url.trim()) || Boolean(uploadedFile);

  useEffect(() => {
    const vid = peekPendingVideoUri();
    if (vid) setUploadedFile({ type: 'video', uri: vid });
  }, []);

  const handleLinkUpload = useCallback(async (targetUrl: string) => {
    if (!targetUrl.trim() || targetUrl === submittedUrl) return;
    setSubmittedUrl(targetUrl);
    setLinkUploadStatus('uploading');
    setLinkVideoId(null);
    setShowLinkModeButtons(false);
    try {
      const res = await withAuth((token) => linkVideo(token, targetUrl));
      setLinkVideoId(res.video_id);
      setLinkUploadStatus('done');
    } catch {
      setLinkUploadStatus('error');
    }
  }, [submittedUrl]);

  const handleUrlChange = useCallback(
    (text: string) => {
      setUrl(text);
      const detected = detectPlatformFromUrl(text);
      if (detected) {
        setSelectedPlatform(detected);
      }
      // YouTube URL이 감지되면 600ms 디바운스 후 링크 업로드
      if (linkDebounceRef.current) clearTimeout(linkDebounceRef.current);
      setShowLinkModeButtons(false);
      if (detected === 'youtube' && text.trim()) {
        linkDebounceRef.current = setTimeout(() => {
          handleLinkUpload(text.trim());
        }, 600);
      } else {
        // YouTube가 아닌 경우 상태 초기화
        if (detected !== null && detected !== 'youtube') {
          setLinkUploadStatus('idle');
          setSubmittedUrl('');
          setLinkVideoId(null);
        }
      }
    },
    [handleLinkUpload],
  );

  const handleAnalyze = () => {
    if (uploadedFile) {
      setShowModeButtons(true);
      return;
    }
    const trimmed = url.trim();
    if (!trimmed) return;
    if (linkUploadStatus === 'done' && linkVideoId) {
      setShowLinkModeButtons(true);
      return;
    }
    if (linkUploadStatus === 'uploading') {
      Alert.alert('업로드 중', '링크 업로드가 완료될 때까지 잠시 기다려주세요.');
      return;
    }
    if (linkUploadStatus === 'error') {
      Alert.alert('업로드 실패', '링크 업로드에 실패했습니다. 다시 시도해주세요.');
      return;
    }
    Alert.alert('알림', 'YouTube URL을 입력하면 자동으로 업로드됩니다.');
  };

  const handleModeSelect = (mode: 'fast' | 'deep') => {
    if (!uploadedFile) return;
    if (uploadedVideoId) {
      router.replace(`/analysis-result?videoId=${uploadedVideoId}&mode=${mode}`);
    } else {
      setPendingVideoUri(uploadedFile.uri);
      router.replace(`/analysis-result?pendingVideo=1&mode=${mode}`);
    }
  };

  const handleLinkModeSelect = (mode: 'fast' | 'deep') => {
    if (!linkVideoId) return;
    router.replace(`/analysis-result?videoId=${linkVideoId}&mode=${mode}`);
  };

  const handleCancel = () => {
    router.back();
  };

  const requestMediaPermission = async () => {
    const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!granted) {
      Alert.alert(
        '권한 필요',
        '갤러리에서 영상을 선택하려면 권한이 필요합니다. 설정에서 권한을 허용해주세요.',
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
      setUploadedFile({ type: 'video', uri });
      setShowModeButtons(false);
      // 백엔드 S3에 업로드
      setVideoUploading(true);
      setUploadedVideoId(null);
      try {
        const res = await withAuth((token) => uploadVideo(token, uri));
        setUploadedVideoId(res.video_id);
      } catch (e: any) {
        Alert.alert('업로드 실패', e?.message ?? '영상 업로드 중 오류가 발생했습니다.');
      } finally {
        setVideoUploading(false);
      }
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <ThemedText style={styles.headerTitle}>링크 붙여넣거나 업로드하기</ThemedText>
          <TouchableOpacity onPress={handleCancel} style={styles.closeButton} hitSlop={12}>
            <MaterialIcons name="close" size={24} color={TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* 영상 업로드 버튼 (앨범 연동) */}
        <View style={styles.uploadRow}>
          <TouchableOpacity style={styles.uploadButton} activeOpacity={0.8} onPress={pickVideo}>
            <Image
              source={require('@/assets/images/video_icon.png')}
              style={styles.uploadIconImage}
              contentFit="contain"
            />
            <ThemedText style={styles.uploadLabel}>영상 업로드</ThemedText>
          </TouchableOpacity>
        </View>

        {uploadedFile && (
          <View style={styles.uploadDoneWrap}>
            {videoUploading ? (
              <ActivityIndicator size="small" color={ACCENT_GREEN} />
            ) : (
              <MaterialIcons name="check-circle" size={16} color={ACCENT_GREEN} />
            )}
            <ThemedText style={styles.uploadDoneText}>
              {videoUploading ? '업로드 중...' : '업로드 완료'}
            </ThemedText>
          </View>
        )}

        <ThemedText style={styles.linkSectionLabel}>링크 삽입</ThemedText>
        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            placeholder="URL을 입력하거나 링크를 붙여넣어 주세요"
            placeholderTextColor={SECONDARY_TEXT_COLOR}
            value={url}
            onChangeText={handleUrlChange}
            multiline={false}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
          <TouchableOpacity style={styles.pasteIconBtn}>
            <MaterialIcons name="content-paste" size={22} color={ACCENT_GREEN} />
          </TouchableOpacity>
        </View>

    
        {/* Supported Platforms */}
        <View style={styles.platformsSection}>
          <View style={styles.platformsHeader}>
            <MaterialIcons name="check-circle" size={22} color={ACCENT_GREEN} />
            <ThemedText style={styles.platformsTitle}>지원 플랫폼</ThemedText>
          </View>
          <View style={styles.platformsGrid}>
            {PLATFORMS.map((platform) => {
              const isSelected = selectedPlatform === platform.id;
              return (
                <TouchableOpacity
                  key={platform.id}
                  style={[styles.platformButton, isSelected && styles.platformButtonSelected]}
                  activeOpacity={0.8}
                  onPress={() => setSelectedPlatform(platform.id)}>
                  <Image
                    source={PLATFORM_ICONS[platform.id]}
                    style={styles.platformIcon}
                    contentFit="contain"
                  />
                  <ThemedText
                    style={[styles.platformLabel, isSelected && styles.platformLabelSelected]}>
                    {platform.label}
                  </ThemedText>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* 링크 업로드 상태 (YouTube URL 감지 시) */}
        {linkUploadStatus !== 'idle' && (
          <View style={styles.linkStatusWrap}>
            {linkUploadStatus === 'uploading' && (
              <>
                <ActivityIndicator size="small" color={ACCENT_GREEN} />
                <ThemedText style={styles.linkStatusText}>링크 업로드 중...</ThemedText>
              </>
            )}
            {linkUploadStatus === 'done' && (
              <>
                <MaterialIcons name="check-circle" size={16} color={ACCENT_GREEN} />
                <ThemedText style={styles.linkStatusText}>링크 업로드 완료</ThemedText>
              </>
            )}
            {linkUploadStatus === 'error' && (
              <>
                <MaterialIcons name="error-outline" size={16} color="#E53E3E" />
                <ThemedText style={[styles.linkStatusText, styles.linkStatusError]}>
                  링크 업로드 실패
                </ThemedText>
              </>
            )}
          </View>
        )}

        {/* 모드 선택 (영상 파일 업로드 후 분석하기 탭 시 표시) */}
        {showModeButtons && uploadedFile && (
          <View style={styles.modeSection}>
            <ThemedText style={styles.modeSectionLabel}>분석 모드 선택</ThemedText>
            <View style={styles.modeButtonsRow}>
              <TouchableOpacity
                style={styles.modeButton}
                activeOpacity={0.8}
                onPress={() => handleModeSelect('fast')}>
                <ThemedText style={styles.modeButtonText}>증거수집모드</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modeButton}
                activeOpacity={0.8}
                onPress={() => handleModeSelect('deep')}>
                <ThemedText style={styles.modeButtonText}>정밀탐지모드</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* 모드 선택 (링크 업로드 완료 후 분석하기 탭 시 표시) */}
        {showLinkModeButtons && linkVideoId && (
          <View style={styles.modeSection}>
            <ThemedText style={styles.modeSectionLabel}>분석 모드 선택</ThemedText>
            <View style={styles.modeButtonsRow}>
              <TouchableOpacity
                style={styles.modeButton}
                activeOpacity={0.8}
                onPress={() => handleLinkModeSelect('fast')}>
                <ThemedText style={styles.modeButtonText}>증거수집모드</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modeButton}
                activeOpacity={0.8}
                onPress={() => handleLinkModeSelect('deep')}>
                <ThemedText style={styles.modeButtonText}>정밀탐지모드</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity style={styles.cancelButton} activeOpacity={0.8} onPress={handleCancel}>
            <ThemedText style={styles.cancelButtonText}>취소</ThemedText>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.analyzeButton, !canAnalyze && styles.analyzeButtonDisabled]}
            activeOpacity={0.8}
            onPress={handleAnalyze}
            disabled={!canAnalyze}>
            <ThemedText style={styles.analyzeButtonText}>분석하기</ThemedText>
          </TouchableOpacity>
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
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  closeButton: {
    padding: 4,
  },
  uploadRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  uploadButton: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  uploadIconImage: {
    width: 60,
    height: 60,
    marginBottom: 4,
  },
  uploadLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: TEXT_COLOR,
  },
  uploadDoneWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 16,
  },
  uploadDoneText: {
    fontSize: 13,
    fontWeight: '600',
    color: ACCENT_GREEN,
  },
  modeSection: {
    marginBottom: 20,
  },
  modeSectionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginBottom: 10,
  },
  modeButtonsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  modeButton: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: ACCENT_GREEN,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: ACCENT_GREEN,
  },
  linkSectionLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 10,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  input: {
    flex: 1,
    paddingVertical: 16,
    fontSize: 16,
    color: TEXT_COLOR,
  },
  pasteIconBtn: {
    padding: 4,
  },
  tipBox: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    padding: 16,
    marginBottom: 24,
    gap: 12,
  },
  tipContent: {
    flex: 1,
  },
  tipTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: TEXT_COLOR,
    marginBottom: 8,
  },
  tipText: {
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    lineHeight: 20,
  },
  platformsSection: {
    marginBottom: 32,
  },
  platformsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  platformsTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  platformsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  platformButton: {
    width: '48%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
    padding: 14,
    gap: 10,
  },
  platformIcon: {
    width: 28,
    height: 28,
  },
  platformButtonSelected: {
    borderColor: ACCENT_GREEN,
    backgroundColor: 'rgba(0, 207, 144, 0.08)',
  },
  platformLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
  },
  platformLabelSelected: {
    color: ACCENT_GREEN_DARK,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.1)',
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: TEXT_COLOR,
  },
  analyzeButton: {
    flex: 1,
    backgroundColor: ACCENT_GREEN,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  analyzeButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  analyzeButtonDisabled: {
    opacity: 0.6,
  },
  linkStatusWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 20,
  },
  linkStatusText: {
    fontSize: 13,
    fontWeight: '600',
    color: ACCENT_GREEN,
  },
  linkStatusError: {
    color: '#E53E3E',
  },
});
