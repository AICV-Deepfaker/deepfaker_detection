# 분석 API 응답 스펙 (프론트 대시보드 연동용)

프론트엔드 **분석 결과 대시보드**는 아래 구조를 기대합니다.  
지금 백엔드는 **공통 필드 + 주파수/시각화**만 반환하고, 나머지는 백엔드 확장 시 채우면 됩니다.

---

## 1. 현재 백엔드가 반환하는 것

`/predict` (POST, file + mode) 현재 응답 예:

```json
{
  "status": "success",
  "result": "FAKE",
  "average_fake_prob": 0.7234,
  "confidence_score": "72.34%",
  "visual_report": "<base64 PNG 문자열>",
  "analysis_mode": "fast"
}
```

→ **주파수 결과 + 시각화 1장**에 해당합니다.  
프론트에서는 이걸 **주파수** 카드와 (증거수집모드일 때) **rPPG** 카드에 공통으로 씁니다.

---

## 2. 모드별로 대시보드가 기대하는 전체 구조

### 2-1. 증거수집모드 (`mode=fast`)

| 항목 | 필드 | 타입 | 설명 |
|------|------|------|------|
| **주파수** | `frequency` | 객체 | result, probability, confidence_score, accuracy, 시각화(base64) |
| **rPPG** | `rppg` | 객체 | result, probability, confidence_score, accuracy, 시각화(base64) |
| **STT 키워드** | `stt_keywords` | 배열 | 키워드별 감지 여부 (투자, 도박, 코인, 대출, 송금, 환급) |

**객체 하나 예시 (frequency / rppg):**

```json
{
  "result": "FAKE",
  "probability": 0.72,
  "confidence_score": "72.34%",
  "accuracy": "95%",
  "visual_base64": "<base64 PNG 문자열>"
}
```

**STT 예시:**

```json
"stt_keywords": [
  { "keyword": "투자", "detected": true },
  { "keyword": "도박", "detected": false },
  { "keyword": "코인", "detected": true },
  { "keyword": "대출", "detected": false },
  { "keyword": "송금", "detected": false },
  { "keyword": "환급", "detected": false }
]
```

### 2-2. 정밀탐지모드 (`mode=deep`)

| 항목 | 필드 | 타입 | 설명 |
|------|------|------|------|
| **UNITE** | `unite` | 객체 | result, probability, confidence_score, accuracy (시각화 없어도 됨) |

**예시:**

```json
"unite": {
  "result": "FAKE",
  "probability": 0.68,
  "confidence_score": "68.00%",
  "accuracy": "94%"
}
```

---

## 3. 권장 응답 형태 (한 번에 다 주는 경우)

아래처럼 **공통 + 모드별 세부**를 한 응답에 넣으면 프론트에서 그대로 대시보드에 매핑합니다.

```json
{
  "status": "success",
  "result": "FAKE",
  "average_fake_prob": 0.72,
  "confidence_score": "72.34%",
  "visual_report": "<기존 주파수 시각화 base64>",
  "analysis_mode": "fast",

  "frequency": {
    "result": "FAKE",
    "probability": 0.72,
    "confidence_score": "72.34%",
    "accuracy": "95%",
    "visual_base64": "<주파수 에너지맵 base64>"
  },
  "rppg": {
    "result": "FAKE",
    "probability": 0.65,
    "confidence_score": "65.00%",
    "accuracy": "93%",
    "visual_base64": "<rPPG 히트맵/웨이브폼 base64>"
  },
  "stt_keywords": [
    { "keyword": "투자", "detected": true },
    { "keyword": "도박", "detected": false },
    { "keyword": "코인", "detected": true },
    { "keyword": "대출", "detected": false },
    { "keyword": "송금", "detected": false },
    { "keyword": "환급", "detected": false }
  ],

  "unite": {
    "result": "FAKE",
    "probability": 0.70,
    "confidence_score": "70.00%",
    "accuracy": "94%"
  }
}
```

- **증거수집(fast)** 일 때: `frequency`, `rppg`, `stt_keywords` 있으면 각 카드에 표시.  
  없으면 지금처럼 **공통** `result` / `average_fake_prob` / `confidence_score` / `visual_report` 로 주파수·rPPG 영역을 채움.
- **정밀탐지(deep)** 일 때: `unite` 있으면 UNITE 카드에 표시.  
  없으면 공통 필드로 UNITE 카드를 채움.

---

## 4. 정리: 지금 반환해야 하는 것 vs 나중에 추가할 것

| 구분 | 지금 있는 것 | 나중에 백엔드에서 추가하면 좋은 것 |
|------|--------------|-------------------------------------|
| **공통** | result, average_fake_prob, confidence_score, visual_report, analysis_mode | (유지) |
| **증거수집(fast)** | 위 공통 → 주파수/시각화로 사용 | `frequency` 객체, `rppg` 객체, `stt_keywords` 배열 |
| **정밀탐지(deep)** | 위 공통 → UNITE 한 칸으로 사용 | `unite` 객체 |

지금은 **주파수 결과 + 시각화만** 반환해도 되고,  
rPPG/STT/UNITE를 구현하는 대로 위 필드만 채워 주면 프론트는 수정 없이 대시보드에 반영됩니다.
