import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useVideoPlayer, VideoView } from 'expo-video';
import * as WebBrowser from 'expo-web-browser';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

import { ThemedText } from '@/components/themed-text';
import { useAnalysis } from '@/contexts/analysis-context';
import { predictWithFile, predictWithImageFile, type PredictResult } from '@/lib/api';
import { takePendingImageUri, takePendingVideoUri } from '@/lib/pending-upload';

/** 딥페이크 관련 최신 사례 정보 */
const DEEPFAKE_CASE_INFO = `🔈 오디오 추출 분석 결과 

"해당 콘텐츠는 유명 축구선수 손흥민 선수의 얼굴과 목소리를 AI로 합성하여 만들어낸 '딥페이크(Deepfake)' 콘텐츠입니다."

최근 이와 같이 정교하게 조작된 영상을 이용해 사용자를 현혹하는 신종 피싱 범죄가 급증하고 있습니다. 공신력 있는 인물을 내세워 신뢰를 얻은 뒤, 자산을 탈취하는 수법이 더욱 대담해지고 있어 각별한 주의가 필요합니다.

📈 실제 피해 사례 및 통계 (2024-2025 기준)
유명인 사칭 및 딥페이크 관련 범죄는 단순한 유희를 넘어 심각한 사회적 비용을 발생시키고 있습니다.

• 사칭형 피싱 피해 급증: 방송통신심의위원회에 따르면, 유명인 사칭 정보 등에 대한 시정요구 건수는 2023년 말 대비 약 10배 이상 폭증했습니다.

• 금전적 피해 규모: 경찰청 집계 결과, 유명인 사칭 투자 사기(메신저/영상 피싱 포함)로 인한 피해액은 최근 1년간 확인된 것만 약 1,200억 원을 상회합니다.

• 딥페이크 영상 유포량: 전 세계적으로 생성된 딥페이크 콘텐츠 중 약 90% 이상이 당사자의 동의 없이 악용된 사례이며, 그중 금융 사기와 연관된 비중이 전년 대비 30% 증가했습니다.

• 검거 및 수사 현황: 손흥민 선수 및 앵커 사칭 사건을 포함하여 현재 경찰이 수사 중인 '강원랜드 사칭 조직' 관련 피해자만 수백 명에 달하는 것으로 추정됩니다.
=============================
🚨 피해 예방을 위한 핵심 체크리스트
• 초고수익 보장 의심: 유명인이 직접 나와 "단기간 고수익"을 보장한다면 99% 확률로 딥페이크 사기입니다.

• 비공식 앱 설치 금지: SNS 링크를 통해 설치 유도하는 '강원랜드 사칭 앱' 등은 개인정보 탈취용 악성 소프트웨어입니다.

• DDP 앱 활용: 이와 같이 딥페이크 영상인지 의심된다면, DDP 앱을 활용하여 꼭 분석을 진행한 후 해당 콘텐츠를 신고하시길 바랍니다.
==============================
더 필요하신 정보나 분석 결과가 있으실까요? 
없으시다면, 해당 거짓 콘텐츠를 신고하시겠습니까? 
💰 신고하고 리워드 받아보세요.`;
/** 사용자 입력이 2차 탐지 요청인지 확인 */
function isSecondaryDetectionRequest(text: string): boolean {
  const normalized = text.replace(/\s/g, '').trim();
  return normalized === '2차탐지' || normalized.includes('2차탐지') || text.trim() === '2차 탐지';
}

/** 사용자 입력이 신고 진행 의사인지 확인 (최신 피해 사례 안내 후 "없어", "신고 진행할게" 등) */
function isReportProceedRequest(text: string): boolean {
  const t = text.trim().toLowerCase();
  const normalized = t.replace(/\s/g, '');
  const keywords = ['없어', '신고를진행할게', '신고진행할게', '신고할게', '신고할게요', '신고할래', '신고할래요', '진행할게', '진행할게요'];
  return keywords.some((k) => normalized.includes(k) || t.includes(k.replace(/\s/g, '')));
}

/** 사용자 입력이 사례 정보 요청인지 확인 */
function isCaseInfoRequest(text: string): boolean {
  const lower = text.toLowerCase().trim();
  const keywords = [
    '관련 최신 사례',
    '최신 사례',
    '사례',
    '피해 사례',
    '실제 사례',
    '사칭 사례',
    '딥페이크 사례',
  ];
  return keywords.some((keyword) => lower.includes(keyword.toLowerCase()));
}

/** API 결과를 채팅용 텍스트로 포맷 (FastAPI 응답 구조) */
function formatPredictResult(data: PredictResult): string {
  if (data.status === 'error') {
    return `분석 중 오류가 발생했습니다.\n\n오류: ${data.message || '알 수 없는 오류'}\n\n다시 시도해 주세요.`;
  }

  const lines: string[] = [];
  
  // 구분선
  lines.push('==============================');
  
  // 최종 판정
  if (data.result) {
    const verdict = data.result === 'FAKE' ? '딥페이크/금융사기 의심' : '정상 콘텐츠로 판단';
    lines.push(`📊 최종 판정: ${data.result}`);
    lines.push(`\n이 콘텐츠는 ${verdict}됩니다.`);
  }
  
  // 평균 Fake 확률
  if (data.average_fake_prob !== undefined) {
    lines.push(`\n📈 평균 Fake 확률: ${data.average_fake_prob.toFixed(4)}`);
  }
  
  // 분석 신뢰도
  if (data.confidence_score) {
    lines.push(`🎯 분석 신뢰도: ${data.confidence_score}`);
  }
  
  // 분석 모드
  if (data.analysis_mode) {
    const modeText = data.analysis_mode === 'full' ? '정밀 탐지' : 
                     data.analysis_mode === 'fast' ? '빠른 탐지' : 
                     data.analysis_mode;
    lines.push(`\n🔍 분석 모드: 🤸🏻빠른 탐지`);
  }
  
  // 구분선
  lines.push('\n==============================');
  
  // 추가 설명
  if (data.result === 'FAKE') {
    lines.push('\n⚠️ 이 콘텐츠는 딥페이크 기술로 제작되었을 가능성이 높습니다.');
    lines.push('금융사기나 사기성 콘텐츠일 수 있으니 주의하시기 바랍니다.');
  } else if (data.result === 'REAL') {
    lines.push('\n✅ 이 콘텐츠는 정상적인 콘텐츠로 판단됩니다.');
  }
  
  lines.push('\n==============================');
  lines.push('\n‼️ 더 자세하게 탐지하고 싶으실 경우에는 🩸 2차 혈류 모델 탐지를 실시할 수 있습니다. \n 원하실 경우, 2차 탐지라고 말씀해주세요.');
  return lines.join('\n');
}

/** YouTube URL에서 비디오 ID 추출 (watch, embed, shorts, youtu.be 지원) */
function getYouTubeVideoId(url: string): string | null {
  try {
    const embed = url.match(/youtube\.com\/embed\/([a-zA-Z0-9_-]+)/);
    if (embed) return embed[1];
    const watch = url.match(/youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]+)/);
    if (watch) return watch[1];
    const shorts = url.match(/youtube\.com\/shorts\/([a-zA-Z0-9_-]+)/);
    if (shorts) return shorts[1];
    const short = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
    if (short) return short[1];
    return null;
  } catch {
    return null;
  }
}

/** 링크에 대해 임베드 URL 반환 (YouTube, Twitter/X, TikTok, Instagram) */
function getEmbedUri(url: string): string | null {
  try {
    const ytId = getYouTubeVideoId(url);
    if (ytId)
      return `https://www.youtube-nocookie.com/embed/${ytId}?playsinline=1&autoplay=0&rel=0`;
    const tw = url.match(/(?:twitter\.com|x\.com)\/\w+\/status\/(\d+)/);
    if (tw) return `https://platform.twitter.com/embed/tweet.html?id=${tw[1]}`;
    const tk = url.match(/tiktok\.com\/@[\w.-]+\/video\/(\d+)/);
    if (tk) return `https://www.tiktok.com/embed/v2/${tk[1]}`;
    const igReel = url.match(/instagram\.com\/reel\/([a-zA-Z0-9_-]+)/);
    if (igReel) return `https://www.instagram.com/reel/${igReel[1]}/embed/`;
    const igP = url.match(/instagram\.com\/p\/([a-zA-Z0-9_-]+)/);
    if (igP) return `https://www.instagram.com/p/${igP[1]}/embed/`;
    return null;
  } catch {
    return null;
  }
}

function isVideoLink(text: string): boolean {
  return (
    (text.startsWith('http://') || text.startsWith('https://')) &&
    text.trim().length > 10
  );
}

function getEmbedHtml(embedUri: string): string {
  const escaped = embedUri.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
  return `<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1.0"><style>*{margin:0;padding:0}html,body{width:100%;height:100%;overflow:hidden}iframe{width:100%;height:100%;border:none}</style></head>
<body><iframe src="${escaped}" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture" allowfullscreen></iframe></body></html>`;
}

/** 로컬 영상 재생 (expo-video) - 메시지별로 player가 필요해 컴포넌트로 분리 */
function LocalVideoPlayer({ uri }: { uri: string }) {
  const player = useVideoPlayer(uri, (p) => {
    p.muted = false;
    p.loop = false;
  });
  return (
    <VideoView
      style={localVideoPlayerStyles.video}
      player={player}
      contentFit="contain"
      nativeControls={true}
      allowsFullscreen
    />
  );
}

const localVideoPlayerStyles = StyleSheet.create({
  video: {
    width: '100%',
    height: 220,
    borderRadius: 12,
    marginTop: 12,
  },
});

const ACCENT_GREEN = '#00CF90';
const ACCENT_GREEN_DARK = '#00B87A';
const TEXT_COLOR = '#111';
const SECONDARY_TEXT_COLOR = '#687076';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  /** 홈에서 업로드한 영상 파일 URI (로컬 영상 표시용) */
  videoUri?: string;
  /** 홈에서 업로드한 이미지 파일 URI (로컬 이미지 미리보기용) */
  imageUri?: string;
  /** 분석 결과 시각화 이미지 (Base64) */
  visualReport?: string;
  /** 2차 탐지(혈류/rPPG) 결과 PCC 값이 있으면 rppg_visual 이미지와 함께 표시 */
  rppgResult?: number;
  /** 이 메시지 아래에 콘텐츠 신고 버튼 표시 */
  showReportButton?: boolean;
  /** 최신 피해 사례 안내 메시지인지 (사용자가 "없어" / "신고 진행할게" 시 신고 버튼 메시지 노출용) */
  showCaseInfoFollowUp?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
}

export default function ChatbotScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{
    link?: string;
    videoUri?: string;
    imageUri?: string;
    pendingVideo?: string;
    pendingImage?: string;
  }>();
  const { addToHistory } = useAnalysis();

  const nextSessionIdRef = useRef(0);
  const [sessions, setSessions] = useState<ChatSession[]>(() => [
    { id: 'session-1', title: '새 채팅', messages: [], createdAt: new Date() },
  ]);
  const [currentSessionId, setCurrentSessionId] = useState('session-1');
  const [inputText, setInputText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState<'media' | 'case' | 'rppg' | false>(false);
  const [sessionMenuVisible, setSessionMenuVisible] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);
  const hasProcessedInitialLink = useRef(false);
  const hasProcessedInitialVideo = useRef(false);
  const hasProcessedInitialImage = useRef(false);
  const nextMessageIdRef = useRef(0);

  const currentSession = sessions.find((s) => s.id === currentSessionId) ?? sessions[0];
  const messages = currentSession?.messages ?? [];

  const nextId = useCallback(() => `msg-${++nextMessageIdRef.current}`, []);
  const nextSessionId = useCallback(() => `session-${++nextSessionIdRef.current}`, []);

  const appendToCurrentSession = useCallback((...newMessages: ChatMessage[]) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? {
              ...s,
              messages: [...s.messages, ...newMessages],
              title:
                s.messages.length === 0 && newMessages[0]?.type === 'user'
                  ? newMessages[0].content.slice(0, 30).trim() || '새 채팅'
                  : s.title,
            }
          : s
      )
    );
  }, [currentSessionId]);

  /** 링크 분석 (시뮬레이션 - FastAPI 영상 파일 업로드만 지원) */
  const analyzeLink = useCallback(
    async (link: string, addUserMessage: boolean) => {
      setIsAnalyzing('media');
      if (addUserMessage) {
        const userMsg: ChatMessage = {
          id: nextId(),
          type: 'user',
          content: link,
          timestamp: new Date(),
        };
        appendToCurrentSession(userMsg);
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const result = `분석이 완료되었습니다.\n\n링크: ${link}\n\n분석 결과: 이 영상은 딥페이크/금융사기 의심 콘텐츠로 판단됩니다. 신고를 진행하시겠습니까?`;
      addToHistory(link, result);
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: result,
        timestamp: new Date(),
        showReportButton: true,
      };
      appendToCurrentSession(assistantMsg);
      setIsAnalyzing(false);
    },
    [addToHistory, nextId, appendToCurrentSession],
  );

  /** 딥페이크 관련 최신 사례 정보 제공 (로딩 포함) */
  const handleCaseInfoRequest = useCallback(
    async () => {
      setIsAnalyzing('case');
      // 실제 분석하는 것처럼 보이기 위한 딜레이 (2-3초)
      await new Promise((resolve) => setTimeout(resolve, 2500));
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: DEEPFAKE_CASE_INFO,
        timestamp: new Date(),
        showCaseInfoFollowUp: true,
      };
      appendToCurrentSession(assistantMsg);
      setIsAnalyzing(false);
    },
    [nextId, appendToCurrentSession],
  );

  /** 2차 탐지(혈류 모델/rPPG) 실시: 로딩 후 rppg 시각화 이미지 + PCC 결과 표시 */
  const handleSecondaryDetection = useCallback(
    async () => {
      setIsAnalyzing('rppg');
      // 2차 탐지 로딩 (실제 분석 중인 것처럼 보이도록 4.5초 대기)
      await new Promise((resolve) => setTimeout(resolve, 4500));
      const pcc = -0.515;
      const resultContent =
        `🩸 2차 탐지(혈류 모델) 결과\n\n` +
        `• PCC (피어슨 상관계수): ${pcc}\n\n` +
        `좌측·우측 필터링된 rPPG 신호 간 상관관계가 ${pcc}로, 역상관 관계를 보입니다. ` +
        `이 지표는 딥페이크에 대한 확실한 지표가 됩니다.\n\n` +
        `\n\n‼️ 원하신다면, 🎙️ 오디오를 추출하여 해당 콘텐츠를 분석하여 \n현재 콘텐츠와 유사한 ❇️ 최신 피해 사례 ❇️에 대해 말씀드릴 수 있습니다.`;
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: resultContent,
        timestamp: new Date(),
        rppgResult: pcc,
      };
      appendToCurrentSession(assistantMsg);
      setIsAnalyzing(false);
    },
    [nextId, appendToCurrentSession],
  );

  /** 영상 파일 분석 (FastAPI predictWithFile 사용) - 홈에서 업로드한 영상 */
  const analyzeVideo = useCallback(
    async (videoUri: string, addUserMessage: boolean) => {
      setIsAnalyzing('media');
      if (addUserMessage) {
        const userMsg: ChatMessage = {
          id: nextId(),
          type: 'user',
          content: '영상 파일을 업로드했습니다.',
          timestamp: new Date(),
          videoUri,
        };
        appendToCurrentSession(userMsg);
      }
      let result: string;
      let visualReport: string | undefined;
      let resultType: 'FAKE' | 'REAL' | undefined;
      try {
        const apiResult = await predictWithFile(videoUri, 'deep');
        result = formatPredictResult(apiResult);
        visualReport = apiResult.visual_report;
        resultType = apiResult.result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : '서버 연결 실패';
        result = `분석 중 오류가 발생했습니다.\n\n오류: ${msg}\n\n• 서버를 재시작했다면 ngrok 주소가 바뀌었을 수 있습니다. lib/api.ts의 API_BASE를 확인해 주세요.\n• FastAPI 터미널 로그에서 상세 오류를 확인해 보세요.`;
      }
      addToHistory('영상 파일', result, resultType, visualReport);
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: result,
        timestamp: new Date(),
        visualReport,
      };
      appendToCurrentSession(assistantMsg);
      setIsAnalyzing(false);
    },
    [addToHistory, nextId, appendToCurrentSession],
  );

  useEffect(() => {
    const link = params.link;
    if (link && typeof link === 'string' && !hasProcessedInitialLink.current) {
      hasProcessedInitialLink.current = true;
      analyzeLink(decodeURIComponent(link), true);
    }
  }, [params.link, analyzeLink]);

  useEffect(() => {
    const fromParam = params.videoUri && decodeURIComponent(params.videoUri);
    const fromStore = takePendingVideoUri();
    const uri = fromParam || fromStore;
    if (uri && !hasProcessedInitialVideo.current) {
      hasProcessedInitialVideo.current = true;
      analyzeVideo(uri, true);
    }
  }, [params.videoUri, params.pendingVideo, analyzeVideo]);

  /** 이미지 파일 분석 (FastAPI predictWithImageFile 사용) - 홈에서 업로드한 이미지 */
  const analyzeImage = useCallback(
    async (imageUri: string, addUserMessage: boolean) => {
      setIsAnalyzing('media');
      if (addUserMessage) {
        const userMsg: ChatMessage = {
          id: nextId(),
          type: 'user',
          content: '이미지 파일을 업로드했습니다.',
          timestamp: new Date(),
          imageUri,
        };
        appendToCurrentSession(userMsg);
      }
      let result: string;
      let visualReport: string | undefined;
      let resultType: 'FAKE' | 'REAL' | undefined;
      try {
        const apiResult = await predictWithImageFile(imageUri, 'deep');
        result = formatPredictResult(apiResult);
        visualReport = apiResult.visual_report;
        resultType = apiResult.result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : '서버 연결 실패';
        result = `분석 중 오류가 발생했습니다.\n\n오류: ${msg}\n\n• 서버를 재시작했다면 ngrok 주소가 바뀌었을 수 있습니다. lib/api.ts의 API_BASE를 확인해 주세요.\n• FastAPI 터미널 로그에서 상세 오류를 확인해 보세요.`;
      }
      addToHistory('이미지 파일', result, resultType, visualReport);
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: result,
        timestamp: new Date(),
        visualReport,
      };
      appendToCurrentSession(assistantMsg);
      setIsAnalyzing(false);
    },
    [addToHistory, nextId, appendToCurrentSession],
  );

  useEffect(() => {
    const fromParam = params.imageUri && decodeURIComponent(params.imageUri);
    const fromStore = takePendingImageUri();
    const uri = fromParam || fromStore;
    if (uri && !hasProcessedInitialImage.current) {
      hasProcessedInitialImage.current = true;
      analyzeImage(uri, true);
    }
  }, [params.imageUri, params.pendingImage, analyzeImage]);

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || isAnalyzing) return;
    setInputText('');
    const userMsg: ChatMessage = {
      id: nextId(),
      type: 'user',
      content: trimmed,
      timestamp: new Date(),
    };
    appendToCurrentSession(userMsg);
    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg?.type === 'assistant' &&
      lastMsg.showCaseInfoFollowUp &&
      isReportProceedRequest(trimmed)
    ) {
      const reportMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: '아래 버튼을 통해 신고해주세요!',
        timestamp: new Date(),
        showReportButton: true,
      };
      appendToCurrentSession(reportMsg);
      return;
    }
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      analyzeLink(trimmed, false);
    } else if (isSecondaryDetectionRequest(trimmed)) {
      handleSecondaryDetection();
    } else if (isCaseInfoRequest(trimmed)) {
      handleCaseInfoRequest();
    } else {
      const assistantMsg: ChatMessage = {
        id: nextId(),
        type: 'assistant',
        content: '영상 링크를 보내주시면 분석해 드립니다. http 또는 https로 시작하는 URL을 입력해주세요.\n\n또는 "관련 최신 사례를 알려줘"라고 입력하시면 딥페이크 관련 최신 사례 정보를 제공해 드립니다.',
        timestamp: new Date(),
      };
      appendToCurrentSession(assistantMsg);
    }
  }, [inputText, isAnalyzing, messages, analyzeLink, handleCaseInfoRequest, handleSecondaryDetection, nextId, appendToCurrentSession]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.headerTextContainer}>
            <ThemedText style={styles.headerTitle}>DDP 챗봇</ThemedText>
            <ThemedText style={styles.headerSubtitle} numberOfLines={1}>
              이게 진짜인지 가짜인지 바로 알려드립니다!
            </ThemedText>
          </View>
        </View>
        <TouchableOpacity
          style={styles.headerMenuButton}
          onPress={() => setSessionMenuVisible(true)}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
          <MaterialIcons name="menu" size={26} color={TEXT_COLOR} />
        </TouchableOpacity>
      </View>

      {/* 세션 메뉴 모달: 새 채팅 + 세션 목록 */}
      <Modal
        visible={sessionMenuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setSessionMenuVisible(false)}>
        <TouchableOpacity
          style={styles.sessionMenuOverlay}
          activeOpacity={1}
          onPress={() => setSessionMenuVisible(false)}>
          <TouchableOpacity
            style={[styles.sessionMenuCard, { marginTop: insets.top + 56 }]}
            activeOpacity={1}
            onPress={() => {}}>
            <TouchableOpacity
              style={styles.sessionMenuNewChat}
              onPress={() => {
                const newId = nextSessionId();
                setSessions((prev) => [
                  ...prev,
                  { id: newId, title: '새 채팅', messages: [], createdAt: new Date() },
                ]);
                setCurrentSessionId(newId);
                setSessionMenuVisible(false);
              }}>
              <MaterialIcons name="add" size={22} color={ACCENT_GREEN} />
              <ThemedText style={styles.sessionMenuNewChatText}>새 채팅</ThemedText>
            </TouchableOpacity>
            <View style={styles.sessionMenuDivider} />
            <ScrollView style={styles.sessionList} showsVerticalScrollIndicator={false}>
              <ThemedText style={styles.sessionListTitle}>세션 목록</ThemedText>
              {sessions.map((session) => (
                <TouchableOpacity
                  key={session.id}
                  style={[
                    styles.sessionItem,
                    session.id === currentSessionId && styles.sessionItemActive,
                  ]}
                  onPress={() => {
                    setCurrentSessionId(session.id);
                    setSessionMenuVisible(false);
                  }}>
                  <MaterialIcons
                    name="chat-bubble-outline"
                    size={20}
                    color={session.id === currentSessionId ? ACCENT_GREEN : SECONDARY_TEXT_COLOR}
                  />
                  <ThemedText
                    style={[
                      styles.sessionItemTitle,
                      session.id === currentSessionId && styles.sessionItemTitleActive,
                    ]}
                    numberOfLines={1}>
                    {session.title}
                  </ThemedText>
                  <ThemedText style={styles.sessionItemMeta}>
                    {session.messages.length}개 메시지
                  </ThemedText>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>

      {/* Messages */}
      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={[
          styles.messagesContent,
          { paddingBottom: insets.bottom + 80 },
          messages.length === 0 && !isAnalyzing && styles.messagesContentEmpty,
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled">
        {messages.length === 0 && !isAnalyzing && (
          <View style={styles.emptyState}>
            <Image
              source={require('@/assets/images/ddp_applogo.png')}
              style={styles.emptyStateLogo}
              contentFit="contain"
            />
            <ThemedText style={styles.emptyTitle}>딥페이크 분석 결과 및 최신 피해 사례를{'\n'}알려드립니다.</ThemedText>
            <ThemedText style={styles.emptySubtitle}>
              링크 혹은 파일를 보내시면{'\n'}딥페이크·금융사기 여부를 분석해드려요!
            </ThemedText>
          </View>
        )}
        {messages.map((msg) => {
          const isUserLink = msg.type === 'user' && isVideoLink(msg.content);
          const isUserVideo = msg.type === 'user' && msg.videoUri;
          const isUserImage = msg.type === 'user' && msg.imageUri;
          const embedUri = isUserLink ? getEmbedUri(msg.content) : null;
          return (
            <View
              key={msg.id}
              style={[styles.messageRow, msg.type === 'user' ? styles.userRow : styles.assistantRow]}>
              {msg.type === 'assistant' && (
                <Image
                  source={require('@/assets/images/ddp_logo.png')}
                  style={styles.messageAvatar}
                  contentFit="contain"
                />
              )}
              <View
                style={[
                  styles.messageBubble,
                  msg.type === 'user' ? styles.userBubble : styles.assistantBubble,
                  (isUserLink || isUserVideo || isUserImage) && styles.messageBubbleWithVideo,
                ]}>
                {msg.type === 'assistant' && msg.visualReport && (
                  <View style={styles.videoPreview}>
                    <Image
                      source={{ uri: `data:image/png;base64,${msg.visualReport}` }}
                      style={styles.visualReportImage}
                      contentFit="contain"
                      cachePolicy="memory-disk"
                    />
                  </View>
                )}
                {msg.type === 'assistant' && msg.rppgResult !== undefined && (
                  <View style={styles.videoPreview}>
                    <Image
                      source={require('@/assets/images/rppg_visual.png')}
                      style={styles.visualReportImage}
                      contentFit="contain"
                    />
                  </View>
                )}
                <ThemedText
                  style={[styles.messageText, msg.type === 'user' ? styles.userText : styles.assistantText]}
                  selectable>
                  {msg.content}
                </ThemedText>
                {msg.type === 'assistant' && msg.showReportButton && (
                  <TouchableOpacity
                    style={styles.reportButton}
                    onPress={() => router.push('/fraud-report')}
                    activeOpacity={0.8}>
                    <MaterialIcons name="report" size={20} color="#fff" />
                    <ThemedText style={styles.reportButtonText}>콘텐츠 신고</ThemedText>
                  </TouchableOpacity>
                )}
                {isUserImage && msg.imageUri && (
                  <View style={styles.videoPreview}>
                    <Image
                      key={msg.imageUri}
                      source={{ uri: msg.imageUri }}
                      style={styles.uploadedImagePreview}
                      contentFit="contain"
                      cachePolicy="memory-disk"
                    />
                  </View>
                )}
                {isUserVideo && msg.videoUri && (
                  <View style={styles.videoPreview}>
                    <LocalVideoPlayer uri={msg.videoUri} />
                  </View>
                )}
                {isUserLink && (
                  <View style={styles.videoPreview}>
                    {embedUri ? (
                      <>
                        <WebView
                          source={{ html: getEmbedHtml(embedUri) }}
                          style={[styles.videoEmbed, styles.videoEmbedShorts]}
                          scrollEnabled={false}
                          allowsFullscreenVideo
                          allowsInlineMediaPlayback
                          originWhitelist={['*']}
                        />
                        <TouchableOpacity
                          style={styles.openInBrowserLink}
                          onPress={() => WebBrowser.openBrowserAsync(msg.content)}>
                          <MaterialIcons name="open-in-new" size={16} color="rgba(255,255,255,0.9)" />
                          <ThemedText style={styles.openInBrowserLinkText}>
                            재생이 안 되면 브라우저에서 보기
                          </ThemedText>
                        </TouchableOpacity>
                      </>
                    ) : (
                      <TouchableOpacity
                        style={styles.openVideoButton}
                        onPress={() => WebBrowser.openBrowserAsync(msg.content)}>
                        <MaterialIcons name="play-circle-outline" size={24} color="#fff" />
                        <ThemedText style={styles.openVideoButtonText}>영상 보기</ThemedText>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
              </View>
            </View>
          );
        })}
        {isAnalyzing && (
          <View style={styles.messageRow}>
            <Image
              source={require('@/assets/images/ddp_logo.png')}
              style={styles.messageAvatar}
              contentFit="contain"
            />
            <View style={[styles.messageBubble, styles.assistantBubble]}>
              <ThemedText style={[styles.messageText, styles.assistantText]}>
                {isAnalyzing === 'case'
                  ? '🎙️ 오디오를 추출하여 키워드 분석 중입니다.'
                  : isAnalyzing === 'rppg'
                    ? '🩸 2차 탐지 실시중'
                    : '💡 분석 중입니다...'}
              </ThemedText>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Input: 링크 입력 + 전송 */}
      <View style={[styles.inputContainer, { paddingBottom: insets.bottom + 16 }]}>
        <TextInput
          style={styles.input}
          placeholder="내용을 입력하세요"
          placeholderTextColor={SECONDARY_TEXT_COLOR}
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={2000}
          editable={!isAnalyzing}
        />
        <TouchableOpacity
          style={[styles.sendButton, (!inputText.trim() || !!isAnalyzing) && styles.sendButtonDisabled]}
          onPress={handleSend}
          disabled={!inputText.trim() || Boolean(isAnalyzing)}>
          <MaterialIcons
            name="send"
            size={24}
            color={inputText.trim() && !isAnalyzing ? '#fff' : SECONDARY_TEXT_COLOR}
          />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  headerLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 8,
  },
  headerTextContainer: {
    flex: 1,
    minWidth: 0, // 텍스트 오버플로우 방지
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: TEXT_COLOR,
  },
  headerSubtitle: {
    fontSize: 13,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 2,
  },
  headerMenuButton: {
    padding: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sessionMenuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    paddingHorizontal: 20,
    alignItems: 'flex-end',
  },
  sessionMenuCard: {
    width: '100%',
    maxWidth: 320,
    maxHeight: '70%',
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingVertical: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  sessionMenuNewChat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  sessionMenuNewChatText: {
    fontSize: 16,
    fontWeight: '600',
    color: ACCENT_GREEN,
  },
  sessionMenuDivider: {
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.08)',
    marginVertical: 4,
  },
  sessionList: {
    maxHeight: 360,
    paddingHorizontal: 12,
    paddingBottom: 12,
  },
  sessionListTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: SECONDARY_TEXT_COLOR,
    marginBottom: 8,
    paddingHorizontal: 8,
  },
  sessionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 4,
  },
  sessionItemActive: {
    backgroundColor: 'rgba(0, 207, 144, 0.12)',
  },
  sessionItemTitle: {
    flex: 1,
    fontSize: 15,
    color: TEXT_COLOR,
  },
  sessionItemTitleActive: {
    fontWeight: '600',
    color: ACCENT_GREEN_DARK,
  },
  sessionItemMeta: {
    fontSize: 12,
    color: SECONDARY_TEXT_COLOR,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  messagesContentEmpty: {
    flexGrow: 1,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
  },
  emptyStateLogo: {
    width: 800,
    height: 220,
    marginBottom: 32,
  },
  emptyTitle: {
    textAlign: 'center',
    fontSize: 18,
    fontWeight: '600',
    color: TEXT_COLOR,
    marginTop: 16,
  },
  emptySubtitle: {
    textAlign: 'center',
    fontSize: 14,
    color: SECONDARY_TEXT_COLOR,
    marginTop: 8,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  userRow: {
    justifyContent: 'flex-end',
  },
  assistantRow: {
    justifyContent: 'flex-start',
  },
  messageAvatar: {
    width: 80,
    height: 80,
    marginRight: -10,
  },
  messageBubble: {
    maxWidth: '80%',
    borderRadius: 16,
    padding: 14,
  },
  messageBubbleWithVideo: {
    maxWidth: '100%',
    minWidth: 280,
  },
  videoPreview: {
    marginTop: 12,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.2)',
  },
  videoEmbed: {
    width: '100%',
    height: 200,
    borderRadius: 12,
  },
  videoEmbedShorts: {
    height: 420,
  },
  uploadedImagePreview: {
    width: '100%',
    height: 220,
    borderRadius: 12,
    marginTop: 12,
    backgroundColor: 'rgba(0,0,0,0.1)',
  },
  visualReportImage: {
    width: '100%',
    minHeight: 200,
    maxHeight: 400,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  openInBrowserLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  openInBrowserLinkText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.9)',
    fontWeight: '500',
  },
  openVideoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  openVideoButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  userBubble: {
    backgroundColor: ACCENT_GREEN,
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: '#fff',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.06)',
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  assistantText: {
    color: TEXT_COLOR,
  },
  reportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: ACCENT_GREEN,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 20,
    marginTop: 16,
  },
  reportButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.06)',
    gap: 12,
  },
  input: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: TEXT_COLOR,
    maxHeight: 120,
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: ACCENT_GREEN,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#E0E0E0',
  },
});
