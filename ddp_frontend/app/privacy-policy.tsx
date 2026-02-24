import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { router } from 'expo-router';
import React from 'react';
import { ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ThemedText } from '@/components/themed-text';

const TEXT = '#111';
const SUB = '#687076';
const BORDER = 'rgba(0,0,0,0.06)';
const ACCENT = '#00CF90';

export default function PrivacyPolicyScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} activeOpacity={0.85}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>개인정보 처리방침</ThemedText>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}>
        <ThemedText style={styles.updatedAt}>최종 업데이트: 2026-02-25</ThemedText>

        <Section title="1. 수집하는 정보">
          <Bullet>로그인 정보: 이메일(아이디), 닉네임, 비밀번호(서버에는 암호화되어 저장될 수 있음)</Bullet>
          <Bullet>서비스 이용 기록: 분석/신고 이력, 포인트/등급 정보</Bullet>
          <Bullet>
            업로드 파일: 사용자가 선택한 영상 파일(딥페이크 탐지/분석 목적){"\n"}
            ※ 앱은 원칙적으로 “필요한 기간 동안만” 처리하며, 정책에 따라 즉시 삭제 또는 일정 기간 보관될 수 있어요.
          </Bullet>
          <Bullet>기기/네트워크 정보: 서비스 안정화 및 오류 대응을 위한 최소한의 로그(선택/자동 수집 범위는 구현에 따름)</Bullet>
        </Section>

        <Section title="2. 이용 목적">
          <Bullet>로그인 및 사용자 식별, 계정 관리</Bullet>
          <Bullet>딥페이크/금융사기 의심 콘텐츠 분석 결과 제공</Bullet>
          <Bullet>신고 접수 처리 및 보상(포인트/리워드) 운영</Bullet>
          <Bullet>서비스 품질 개선(오류 분석, 성능 개선, 악용 방지)</Bullet>
        </Section>

        <Section title="3. 영상물(업로드 콘텐츠) 처리 원칙">
          <Bullet>
            사용자는 업로드하는 영상에 대해 업로드/분석을 요청할 권리가 있어야 합니다(저작권/초상권/개인정보 포함).
          </Bullet>
          <Bullet>
            타인의 얼굴/음성/개인정보가 포함된 콘텐츠를 업로드할 경우, 관련 법령 및 권리(초상권, 개인정보보호 등)를 침해하지 않도록 주의해야 합니다.
          </Bullet>
          <Bullet>
            앱은 제공 목적(탐지/분석/신고) 달성을 위해 필요한 범위에서만 콘텐츠를 처리합니다.
          </Bullet>
          <Note>
            법률 안내: 본 안내는 일반적 정보 제공이며 법률 자문이 아닙니다. 국가/상황에 따라 적용 법령과 해석이 달라질 수 있어요.
          </Note>
        </Section>

        <Section title="4. 보관 및 삭제">
          <Bullet>계정 정보: 회원 탈퇴 시 지체 없이 삭제(관련 법령상 보관 의무가 있는 경우 예외)</Bullet>
          <Bullet>업로드 파일: 분석 목적 달성 후 즉시 삭제 또는 최소 기간 보관(운영 정책에 따름)</Bullet>
          <Bullet>로그/이력: 서비스 운영 및 분쟁 대응을 위해 일정 기간 보관될 수 있음</Bullet>
        </Section>

        <Section title="5. 제3자 제공 및 위탁">
          <Bullet>원칙적으로 개인정보를 제3자에게 제공하지 않습니다.</Bullet>
          <Bullet>
            다만, 서비스 운영을 위해 클라우드/메일/로그 분석 등 외부 업체에 처리를 위탁할 수 있으며, 이 경우 고지 및 계약을 통해 보호 조치를 적용합니다.
          </Bullet>
        </Section>

        <Section title="6. 이용자 권리">
          <Bullet>내 정보 열람/수정/삭제 요청</Bullet>
          <Bullet>회원 탈퇴 및 처리 정지 요청</Bullet>
          <Bullet>문의: 고객지원 &gt; 문의하기</Bullet>
        </Section>

        <ThemedText style={styles.smallPrint}>
          * 실제 운영 정책(보관 기간/위탁사/수집 항목)은 백엔드 구현 및 운영 방식에 따라 달라질 수 있어요.
        </ThemedText>
      </ScrollView>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <ThemedText style={styles.sectionTitle}>{title}</ThemedText>
      <View style={{ gap: 10 }}>{children}</View>
    </View>
  );
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.bulletRow}>
      <View style={styles.dot} />
      <ThemedText style={styles.bulletText}>{children}</ThemedText>
    </View>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.note}>
      <ThemedText style={styles.noteText}>{children}</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: BORDER,
  },
  backBtn: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 18, fontWeight: '800', color: TEXT },

  content: { padding: 16 },

  updatedAt: { fontSize: 12, color: SUB, marginBottom: 12 },

  section: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: BORDER,
    marginBottom: 12,
  },
  sectionTitle: { fontSize: 15, fontWeight: '900', color: TEXT, marginBottom: 12 },

  bulletRow: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: ACCENT,
    marginTop: 7,
  },
  bulletText: { flex: 1, fontSize: 13, color: TEXT, lineHeight: 19 },

  note: {
    marginTop: 6,
    backgroundColor: 'rgba(0,207,144,0.08)',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,207,144,0.18)',
  },
  noteText: { fontSize: 12, color: '#0E5E44', lineHeight: 18, fontWeight: '700' },

  footerCard: {
    marginTop: 6,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: BORDER,
  },
  footerTitle: { fontSize: 14, fontWeight: '900', color: TEXT, marginBottom: 6 },
  footerText: { fontSize: 13, color: SUB, lineHeight: 18, marginBottom: 12 },
  pill: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(0,207,144,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(0,207,144,0.20)',
  },
  pillText: { fontSize: 12, fontWeight: '900', color: '#00B87A' },

  smallPrint: { marginTop: 10, fontSize: 11, color: SUB, lineHeight: 16 },
});