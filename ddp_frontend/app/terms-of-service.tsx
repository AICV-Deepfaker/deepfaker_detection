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
const DANGER = '#E53935';

export default function TermsOfServiceScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} activeOpacity={0.85}>
          <MaterialIcons name="arrow-back" size={24} color={TEXT} />
        </TouchableOpacity>
        <ThemedText style={styles.headerTitle}>서비스 이용약관</ThemedText>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}>
        <ThemedText style={styles.updatedAt}>최종 업데이트: 2026-02-25</ThemedText>

        <Section title="1. 목적">
          <Bullet>
            본 약관은 DDP(이하 “서비스”) 이용과 관련하여 서비스와 이용자 간의 권리·의무 및
            책임사항, 이용 조건 및 절차를 규정합니다.
          </Bullet>
        </Section>

        <Section title="2. 서비스 내용">
          <Bullet>딥페이크/금융사기 의심 콘텐츠(영상 등) 분석 결과 제공</Bullet>
          <Bullet>분석 이력(히스토리) 관리 및 신고 기능 제공</Bullet>
          <Bullet>신고 활동 기반 포인트/등급/리워드(이벤트성 제공 포함) 운영</Bullet>
          <Note>
            ※ 서비스는 기술적 분석 결과를 제공하며, 법적 확정 판단(진위 판정/수사 판단)을
            대체하지 않습니다.
          </Note>
        </Section>

        <Section title="3. 계정 및 로그인">
          <Bullet>이용자는 정확한 정보를 제공해야 하며, 타인의 정보를 도용할 수 없습니다.</Bullet>
          <Bullet>계정 보안(비밀번호/토큰 관리)은 이용자 책임이며, 유출 시 즉시 변경/문의해야 합니다.</Bullet>
          <Bullet>서비스는 보안/정책 위반 의심 시 로그인 제한 또는 추가 인증을 요구할 수 있습니다.</Bullet>
        </Section>

        <Section title="4. 업로드 콘텐츠(영상 등) 관련 이용자 의무">
          <Bullet>
            이용자는 업로드하는 콘텐츠에 대해 업로드/분석을 요청할 권리가 있어야 합니다
            (저작권, 초상권, 개인정보 포함).
          </Bullet>
          <Bullet>
            타인의 얼굴·음성·개인정보가 포함된 콘텐츠는 관련 법령 및 권리를 침해하지 않도록
            주의해야 합니다.
          </Bullet>
        </Section>

        <Section title="5. 신고 기능 및 포인트/리워드">
          <Bullet>신고는 이용자 판단에 따라 진행되며, 허위 신고/반복 신고 등 악용 행위는 금지됩니다.</Bullet>
          <Bullet>
            포인트/등급/리워드는 운영 정책에 따라 변경/중단될 수 있으며, 부정 획득이 확인되면
            회수될 수 있습니다.
          </Bullet>
          <Bullet>
            리워드 제공은 이벤트/재고/운영 사정에 따라 제한될 수 있으며, 세부 조건은 별도 고지합니다.
          </Bullet>
        </Section>

        <Section title="6. 서비스 이용 제한">
          <Bullet>약관 또는 정책 위반, 불법 행위, 시스템 안정성 저해가 확인될 경우 이용을 제한할 수 있습니다.</Bullet>
          <Bullet>필요 시 게시물/이력 삭제, 포인트 회수, 계정 정지/탈퇴 처리 등의 조치를 할 수 있습니다.</Bullet>
        </Section>

        <Section title="7. 책임의 제한">
          <Bullet>
            서비스는 분석 결과의 정확성을 위해 노력하지만, 모든 상황에서 결과를 보장하지 않습니다.
          </Bullet>
          <Bullet>
            서비스 결과를 근거로 한 이용자의 의사결정에 대해 서비스가 법적 책임을 부담하지 않는 범위가
            있을 수 있습니다(관련 법령이 허용하는 한도).
          </Bullet>
        </Section>

        <Section title="8. 약관 변경">
          <Bullet>서비스는 관련 법령을 위반하지 않는 범위에서 약관을 변경할 수 있습니다.</Bullet>
          <Bullet>중요 변경 시 앱 내 공지 등 합리적인 방법으로 사전 고지합니다.</Bullet>
        </Section>

        <ThemedText style={styles.smallPrint}>
          * 본 약관은 실제 운영 정책(보관 기간/리워드 조건/제한 기준)에 따라
          조정이 필요합니다.
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

function DangerNote({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.dangerNote}>
      <ThemedText style={styles.dangerNoteText}>{children}</ThemedText>
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

  dangerNote: {
    marginTop: 6,
    backgroundColor: 'rgba(229,57,53,0.08)',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(229,57,53,0.16)',
  },
  dangerNoteText: { fontSize: 12, color: DANGER, lineHeight: 18, fontWeight: '800' },

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