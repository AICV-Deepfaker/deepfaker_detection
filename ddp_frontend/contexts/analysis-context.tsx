import React, { createContext, useCallback, useContext, useState } from 'react';

export interface HistoryItem {
  id: string;
  link: string;
  result: string; // 포맷된 결과 텍스트
  resultType?: 'FAKE' | 'REAL'; // FastAPI에서 받은 최종 판정
  visualReport?: string; // Base64 이미지 데이터
  resultId?: string; // 신고용 result_id
  date: string;
}

/** 등급별 뱃지 정보 */
export const BADGE_TIERS = [
  { minPoints: 0, name: '신입 탐정', icon: '🔍', desc: '딥페이크 신고의 첫 걸음' },
  { minPoints: 1000, name: '딥페이크 헌터', icon: '🦅', desc: '1회 이상 신고 완료' },
  { minPoints: 10000, name: '진실의 수호자', icon: '🛡️', desc: '10,000P 달성 · 스타벅스 아메리카노 기프티콘' },
  { minPoints: 100000, name: '경찰청장상', icon: '🏅', desc: '100,000P 달성 · 경찰청장상 수상급' },
] as const;

export function getBadgeForPoints(points: number) {
  let current: typeof BADGE_TIERS[number] = BADGE_TIERS[0];
  let next: typeof BADGE_TIERS[number] | null = BADGE_TIERS[1] ?? null;
  for (let i = BADGE_TIERS.length - 1; i >= 0; i--) {
    if (points >= BADGE_TIERS[i].minPoints) {
      current = BADGE_TIERS[i];
      next = BADGE_TIERS[i + 1] ?? null;
      break;
    }
  }
  return { current, next };
}

export const POINTS_PER_REPORT = 1000;
export const GIFT_THRESHOLD = 10000; // 스타벅스 아메리카노 기프티콘

interface AnalysisContextType {
  reward: number;
  totalPoints: number;
  reportCount: number;
  history: HistoryItem[];
  addToHistory: (
      link: string,
      result: string,
      resultType?: 'FAKE' | 'REAL',
      visualReport?: string,
      resultId?: string,
    ) => string;
  addPoints: (amount: number) => void;
  setPointsFromServer: (data: { activePoints: number; totalPoints: number }) => void;
  incrementReportCount: () => void;
  getHistoryByLink: (link: string) => HistoryItem[];
}

const AnalysisContext = createContext<AnalysisContextType | null>(null);

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [totalPoints, setTotalPoints] = useState(0);
  const [reportCount, setReportCount] = useState(0);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const reward = totalPoints; // 호환용
  const addPoints = useCallback((amount: number) => {
    setTotalPoints((prev) => prev + amount);
  }, []);

  const incrementReportCount = useCallback(() => {
    setReportCount((prev) => prev + 1);
  }, []);

  const setPointsFromServer = useCallback(
    (data: { activePoints: number; totalPoints: number }) => {
      setTotalPoints(data.totalPoints);
    },
    [],
  );

  const addToHistory = useCallback(
    (link: string, result: string, resultType?: 'FAKE' | 'REAL', visualReport?: string, resultId?: string) => {
      const newItem: HistoryItem = {
        id: Date.now().toString(),
        link,
        result,
        resultType,
        visualReport,
        resultId,
        date: new Date().toISOString(),
      };

      setHistory((prev) => [newItem, ...prev]);

      return newItem.id; // ✅ 이게 없으면 id가 undefined
    },
    []
  );

  const getHistoryByLink = useCallback(
    (link: string) => {
      const normalized = link.trim().toLowerCase();
      return history.filter((item) => item.link.trim().toLowerCase() === normalized);
    },
    [history],
  );

  return (
    <AnalysisContext.Provider
      value={{
        reward,
        totalPoints,
        reportCount,
        history,
        addToHistory,
        addPoints,
        setPointsFromServer,
        incrementReportCount,
        getHistoryByLink,
      }}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within AnalysisProvider');
  }
  return context;
}
