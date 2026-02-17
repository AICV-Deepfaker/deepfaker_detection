import { XMLParser } from 'fast-xml-parser';

export type NewsItem = {
  title: string;
  date: string;
  summary: string;
  link: string;
  source?: string;
};

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '',
});

// 카테고리 → 검색어(너 취향대로 키워드 더 넣어도 됨)
export const CATEGORY_QUERY: Record<string, string> = {
  invest: '딥페이크 투자 사기 OR 유명인 사칭 투자',
  gamble: '딥페이크 도박 광고 OR 불법 도박 사기',
  coin: '딥페이크 코인 사기 OR 가상자산 스캠',
  loan: '딥페이크 대출 사기 OR 무담보 대출 피싱',
  remit: '딥페이크 송금 사기 OR 긴급 송금 요구',
  refund: '딥페이크 환급 사기 OR 보상금 피싱',
};

export async function fetchNewsByCategory(categoryId: string): Promise<NewsItem[]> {
  const q = CATEGORY_QUERY[categoryId] ?? '딥페이크 금융사기';
  const url =
    `https://news.google.com/rss/search?q=${encodeURIComponent(q)}` +
    `&hl=ko&gl=KR&ceid=KR:ko`;

  const res = await fetch(url);
  if (!res.ok) throw new Error(`뉴스 로드 실패 (${res.status})`);

  const xml = await res.text();
  const json = parser.parse(xml);

  const items = json?.rss?.channel?.item ?? [];
  const arr = Array.isArray(items) ? items : [items];

  return arr
    .filter(Boolean)
    .map((it: any) => ({
      title: String(it.title ?? ''),
      date: it.pubDate ? new Date(it.pubDate).toLocaleDateString('ko-KR') : '',
      summary: String(it.description ?? '').replace(/<[^>]+>/g, '').trim(),
      link: String(it.link ?? ''),
      source: it.source?.['#text'] ?? it.source,
    }))
    .filter((x: NewsItem) => x.title);
}