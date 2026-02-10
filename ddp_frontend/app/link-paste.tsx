import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

type PlatformId = 'twitter' | 'youtube' | 'instagram' | 'facebook' | 'tiktok' | 'direct';

const PLATFORMS: { id: PlatformId; label: string; icon: string }[] = [
  { id: 'twitter', label: 'Twitter/X', icon: 'tag' },
  { id: 'youtube', label: 'YouTube', icon: 'play-circle-filled' },
  { id: 'instagram', label: 'Instagram', icon: 'photo-camera' },
  { id: 'facebook', label: 'Facebook', icon: 'people' },
  { id: 'tiktok', label: 'TikTok', icon: 'music-note' },
  { id: 'direct', label: '직접 링크', icon: 'link' },
];

function detectPlatformFromUrl(url: string): PlatformId | null {
  const lower = url.toLowerCase().trim();
  if (!lower) return null;
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube';
  if (lower.includes('instagram.com')) return 'instagram';
  if (lower.includes('twitter.com') || lower.includes('x.com')) return 'twitter';
  if (lower.includes('tiktok.com')) return 'tiktok';
  if (lower.includes('facebook.com') || lower.includes('fb.com') || lower.includes('fb.watch'))
    return 'facebook';
  if (lower.startsWith('http://') || lower.startsWith('https://')) return 'direct';
  return null;
}

export default function LinkPasteScreen() {
  const insets = useSafeAreaInsets();
  const [url, setUrl] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformId | null>(null);

  const handleUrlChange = useCallback(
    (text: string) => {
      setUrl(text);
      const detected = detectPlatformFromUrl(text);
      if (detected) {
        setSelectedPlatform(detected);
      }
    },
    [],
  );

  const handleAnalyze = () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    const encoded = encodeURIComponent(trimmed);
    router.replace(`/(tabs)/chatbot?link=${encoded}`);
  };

  const handleCancel = () => {
    router.back();
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
          <ThemedText style={styles.headerTitle}>링크 붙여넣거나 공유하기</ThemedText>
          <TouchableOpacity onPress={handleCancel} style={styles.closeButton} hitSlop={12}>
            <MaterialIcons name="close" size={24} color={TEXT_COLOR} />
          </TouchableOpacity>
        </View>

        {/* URL Input */}
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

        {/* Tip Section */}
        <View style={styles.tipBox}>
          <MaterialIcons name="lightbulb-outline" size={24} color={ACCENT_GREEN} />
          <View style={styles.tipContent}>
            <ThemedText style={styles.tipTitle}>팁: 링크 공유 또는 붙여넣기</ThemedText>
            <ThemedText style={styles.tipText}>
              Twitter, YouTube, Instagram, Facebook, TikTok에서 DDP로 직접 공유할 수 있습니다. 해당
              앱에서 공유 버튼을 누르고 'DDP - 딥페이크 탐지'를 선택하세요.
            </ThemedText>
          </View>
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
                  <MaterialIcons
                    name={platform.icon as any}
                    size={28}
                    color={isSelected ? ACCENT_GREEN : SECONDARY_TEXT_COLOR}
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

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity style={styles.cancelButton} activeOpacity={0.8} onPress={handleCancel}>
            <ThemedText style={styles.cancelButtonText}>취소</ThemedText>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.analyzeButton, !url.trim() && styles.analyzeButtonDisabled]}
            activeOpacity={0.8}
            onPress={handleAnalyze}
            disabled={!url.trim()}>
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
});
