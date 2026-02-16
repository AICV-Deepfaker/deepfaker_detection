# Google 소셜 로그인 연동 가이드

DDP 앱에서 이미 `expo-auth-session`으로 Google 로그인 코드가 준비되어 있습니다. 아래 순서대로 **Google Cloud Console 설정**과 **앱 환경변수**만 맞추면 됩니다.

---

## 1. Google Cloud Console 설정

### 1-1. 프로젝트 만들기

1. [Google Cloud Console](https://console.cloud.google.com/) 접속 후 로그인
2. 상단 프로젝트 선택 → **새 프로젝트**
3. 프로젝트 이름 입력 (예: `DDP`) → **만들기**

### 1-2. OAuth 동의 화면 설정

1. 왼쪽 메뉴 **API 및 서비스** → **OAuth 동의 화면**
2. **외부** 사용자 유형 선택 → **만들기**
3. 필수 입력:
   - **앱 이름**: DDP (또는 원하는 이름)
   - **사용자 지원 이메일**: 본인 이메일
   - **개발자 연락처**: 본인 이메일
4. **저장 후 계속** → 범위 추가:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
5. **저장 후 계속** → 테스트 사용자(개발 중 본인 이메일) 추가 → **저장**

### 1-3. 승인된 리디렉션 URI — 이렇게 받으면 됩니다

**리디렉션 URI는 Google이 만드는 값이 아니라, 우리 앱이 “로그인 끝나면 여기로 돌려보내라”고 쓰는 주소입니다.**  
그래서 **앱을 한 번 실행해서 나오는 값**을 그대로 Google Console에 등록해야 합니다.

#### 방법 1: 로그인 화면에서 복사 (가장 쉬움)

1. 터미널에서 `npx expo start` 실행 후 앱을 엽니다.
2. **로그인 화면**으로 이동합니다.
3. 화면 아래 **「리디렉션 URI (Google에 등록할 값)」** 문구 옆에 주소가 보입니다.  
   예: `ddp://redirect` 또는 `exp://192.168.0.1:8081/--/redirect` 등
4. **그 문자열 전체를 복사**합니다.
5. Google Cloud Console → **사용자 인증 정보** → OAuth 클라이언트 ID → **승인된 리디렉션 URI**에 **그대로 붙여넣기** 후 저장합니다.

> 클라이언트 ID를 아직 안 만들었다면, 먼저 아래 1-4에서 “웹 애플리케이션” 클라이언트를 만들고, **승인된 리디렉션 URI**란에 위에서 복사한 값을 추가하면 됩니다.

#### 방법 2: 터미널 로그로 확인

1. `npx expo start`로 앱 실행
2. 로그인 화면이 떠 있는 상태에서 **Metro 터미널**(expo가 돌아가는 터미널)을 봅니다.
3. `[Redirect URI] ...` 처럼 찍힌 한 줄을 찾아 **그 안의 URI 전체**를 복사합니다.
4. Google Console **승인된 리디렉션 URI**에 그대로 추가합니다.

**정리:**  
- “승인된 리디렉션 URI”는 **앱이 만들어 쓰는 값**이라, **앱을 실행해서 확인한 값**을 Google에 등록해야 합니다.  
- 보통은 `ddp://redirect` 이지만, Expo Go로 실행 중이면 `exp://192.168.x.x:8081/--/redirect` 처럼 **로컬 IP**가 붙은 값이 나옵니다. 이 값도 **리디렉션 URI 칸**에 넣으면 됩니다 (로컬 주소라서 안 되는 게 아닙니다).
- **"공개 최상위 도메인으로 끝나야 합니다"** 오류: 리디렉션 URI 칸에 `exp://...` 나 `ddp://...` 를 넣어도 **Google이 거부하는 경우**가 있습니다. 이럴 때는 앱에서 **Expo 인증 프록시(useProxy: true)** 를 사용해, 리디렉션 URI가 **`https://auth.expo.io/...`** 형태로 나오게 한 뒤, **그 주소**를 Google Console에 등록하면 됩니다 (아래 "exp/ddp 가 거부될 때" 참고).

---

### 1-4. OAuth 2.0 클라이언트 ID 만들기 (두 칸 구분하기)

웹 애플리케이션 클라이언트에는 **두 가지 입력 칸**이 있습니다. **모바일 앱에서는 아래만 지키면 됩니다.**

| 칸 이름 | 뭐에 쓰는지 | DDP 모바일 앱에서는 |
|--------|-------------|---------------------|
| **승인된 JavaScript 원본** | 브라우저에서 돌아가는 웹 앱용 (예: `https://mysite.com`) | **비워 두기** |
| **승인된 리디렉션 URI** | 로그인 후 돌아올 주소 (앱에서 쓰는 값) | **여기에만** `ddp://redirect` 등 추가 |

#### ⚠️ "올바르지 않은 출처" / "공개 최상위 도메인으로 끝나야 합니다" 오류가 날 때

이 오류는 **`ddp://redirect` 또는 `exp://192.168...` 같은 값을 "승인된 JavaScript 원본" 칸에 넣었을 때** 나는 메시지입니다.  
**"승인된 리디렉션 URI" 칸에만** 넣어야 합니다. 로컬 주소(exp://)라서 막히는 게 아니라, **넣는 칸이 잘못된 것**입니다.

---

### 1-4-a. 화면에서 칸 구분하기 (중요)

Google Cloud Console에서 OAuth 클라이언트를 만들/수정할 때 **폼이 보통 이 순서**입니다:

1. **맨 위:** **승인된 JavaScript 원본** (Authorized JavaScript origins)  
   → 여기에는 **아무 것도 넣지 마세요.**  
   → "URI 추가"를 눌러서 새 줄을 만든 적이 있다면 **전부 삭제**하세요.

2. **그 아래:** **승인된 리디렉션 URI** (Authorized redirect URIs)  
   → **여기에만** `ddp://redirect` 를 넣으세요.  
   → 값은 정확히 `ddp://redirect` (맨 뒤에 `/` 없음, 공백 없음).

**정리:** `ddp://redirect` 는 **아래쪽 "리디렉션 URI" 칸에만** 넣고, **위쪽 "JavaScript 원본" 칸에는 절대 넣지 마세요.**

---

### 1-4-b. 그래도 오류가 나면 — 새 클라이언트로 처음부터

1. **사용자 인증 정보** 목록에서 기존 "웹 애플리케이션" 클라이언트는 **수정하지 말고** 두고,
2. **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID** 로 **새로 하나** 만듭니다.
3. **애플리케이션 유형**: **웹 애플리케이션**
4. **이름**: 예) DDP Mobile
5. **승인된 JavaScript 원본**  
   - "URI 추가"를 **누르지 말고**, 칸이 비어 있는 상태로 두세요.  
   - 이미 항목이 있으면 **휴지통/삭제**로 전부 지우세요.
6. **승인된 리디렉션 URI**  
   - 여기만 "URI 추가"를 누르고, **앱 로그인 화면에 나온 값**을 **그대로** 한 개 추가합니다.  
   - 예: Expo Go면 `exp://192.168.35.83:8081/--/redirect` , 개발 빌드면 `ddp://redirect`  
   - 이 값은 **아래쪽 "리디렉션 URI" 칸에만** 넣고, 위쪽 "JavaScript 원본" 칸에는 넣지 마세요.
7. **만들기** 클릭 후, 새로 나온 **클라이언트 ID**를 복사해 `.env`의 `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`에 넣습니다.

---

### 1-4-c. JavaScript 원본을 비우면 "저장이 안 됩니다" 일 때

일부 계정/콘솔에서는 "승인된 JavaScript 원본"이 **비어 있으면 저장이 막히는** 경우가 있습니다. 그럴 때만 아래를 시도하세요.

- **승인된 JavaScript 원본**에 **딱 하나만** 추가합니다. 아래 중 하나를 쓰세요.  
  - `https://localhost` (경로·끝 `/` 없이)  
  - 또는 본인이 소유한 도메인이 있으면 `https://본인도메인.com` (예: `https://myapp.com`)
- **승인된 리디렉션 URI**에는 그대로 `ddp://redirect` 만 넣습니다.

JavaScript 원본은 **웹용**이고, 모바일 앱 로그인은 **리디렉션 URI**만 사용하므로, 위처럼 하나 넣어도 앱 동작에는 영향 없습니다. `https://localhost`가 거부되면 소유한 도메인을 쓰면 됩니다.

---

1. **API 및 서비스** → **사용자 인증 정보**
2. **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
3. **애플리케이션 유형**: **웹 애플리케이션**
4. **이름**: 예) DDP Web Client
5. **승인된 JavaScript 원본**: 비움 (또는 저장이 막히면 `https://localhost` 하나만)
6. **승인된 리디렉션 URI**: 아래 "exp/ddp 거부될 때" 참고
7. **만들기** 클릭
8. 생성된 **클라이언트 ID** 복사

---

### 1-5. exp:// 또는 ddp:// 가 리디렉션 URI에서 거부될 때

**리디렉션 URI 칸**에 `exp://192.168.x.x:8081/--/redirect` 나 `ddp://redirect` 를 넣었는데,  
**"공개 최상위 도메인으로 끝나야 합니다"** / **"유효한 최상위 비공개 도메인을 사용해야 합니다"** 오류가 나는 경우가 있습니다.  
Google이 커스텀 스킴(exp://, ddp://)을 리디렉션 URI로 허용하지 않는 정책일 수 있습니다.

**해결:** 리디렉션 URI를 **`https://auth.expo.io/@계정명/ddp`** 로 고정해 씁니다.  
이 주소는 `.io` 도메인이라 Google 검사를 통과합니다. **Expo 계정명(owner)** 이 필요합니다.

1. **Expo 계정명 확인**  
   터미널에서 `npx expo whoami` 실행.  
   - **"Not logged in"** 이 나오면 먼저 로그인: `npx expo login` 실행 후 이메일/비밀번호 입력. (계정 없으면 [expo.dev](https://expo.dev)에서 무료 가입)  
   - 로그인된 뒤 다시 `npx expo whoami` 하면 **계정명**이 나옵니다. 그걸 쓰면 됩니다.
2. **.env에 추가** (ddp_frontend 루트에 `.env` 파일):
   ```env
   EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=기존에_만든_클라이언트_ID
   EXPO_PUBLIC_EXPO_OWNER=여기에_Expo계정명
   ```
   예: `EXPO_PUBLIC_EXPO_OWNER=myexpo` 이면 리디렉션 URI는 `https://auth.expo.io/@myexpo/ddp`
3. **앱 다시 실행** (`npx expo start` 후 로그인 화면 이동).  
   화면 하단 **「리디렉션 URI」** 에 **`https://auth.expo.io/@계정명/ddp`** 가 표시되는지 확인합니다.
4. **Google Cloud Console** → **사용자 인증 정보** → 해당 OAuth 클라이언트 수정 → **승인된 리디렉션 URI**에서  
   - 기존 `exp://...` 항목은 **삭제**하고  
   - **`https://auth.expo.io/@계정명/ddp`** 한 개만 추가 (계정명은 .env에 넣은 값과 동일)  
   - 저장
5. Google 로그인 다시 시도.

이후 로그인은 Expo 인증 프록시를 경유해 동작합니다. (Expo Go 개발용)

**리디렉션 URI가 여전히 exp:// 로만 나올 때**  
Expo 최신 버전에서는 `useProxy: true` 만으로는 `https://auth.expo.io/...` 가 안 나올 수 있습니다.  
그럴 때는 **EXPO_PUBLIC_EXPO_OWNER** 를 반드시 .env에 넣고, **앱을 완전히 종료한 뒤** `npx expo start` 로 다시 실행하세요.  
그러면 앱이 `https://auth.expo.io/@계정명/ddp` 를 쓰고, 로그인 화면에도 그 주소가 표시됩니다.

---

## 2. 앱에 클라이언트 ID 넣기

### 방법 A: 환경 변수 (권장)

프로젝트 루트에 `.env` 파일을 만들고:

```env
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=여기에_복사한_클라이언트_ID.apps.googleusercontent.com
```

- `.env`는 Git에 올리지 않도록 `.gitignore`에 추가해 두는 것이 좋습니다.
- Expo는 `EXPO_PUBLIC_` 접두사가 붙은 변수만 앱에서 읽을 수 있습니다.

### 방법 B: app.config.js에서 직접 (선택)

`app.json` 대신 `app.config.js`를 쓰는 경우:

```js
export default {
  expo: {
    // ... 기존 설정
    extra: {
      googleWebClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    },
  },
};
```

로그인 화면에서는 `expo-constants`로 `Constants.expoConfig?.extra?.googleWebClientId`를 읽으면 됩니다.  
지금 구조처럼 `process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`를 쓰면 별도 수정 없이 동작합니다.

---

## 3. 리디렉션 URI 다시 확인하고 싶을 때

로그인 화면 하단에 **「리디렉션 URI (Google에 등록할 값)」** 이 이미 표시되므로, 그 값을 복사해 Google Console에 넣으면 됩니다.  
개발 중에 터미널에서도 보고 싶다면 `app/login.tsx`에서 `useEffect`로 한 번만 로그를 남길 수 있습니다:

```ts
useEffect(() => {
  console.log('[Redirect URI]', redirectUri);
}, [redirectUri]);
```

---

## 4. (선택) 프로키시 제거 후 딥링크만 사용

Expo는 `auth.expo.io` 프로키시를 더 이상 권장하지 않습니다. `scheme: 'ddp'`를 쓰고 프로키시를 끄면:

- **승인된 리디렉션 URI**에는 `ddp://redirect` (또는 위에서 로그로 확인한 값)만 넣으면 됩니다.
- `app.json`에 `"scheme": "ddp"`가 이미 있으므로, `useProxy: false`로 두고 `makeRedirectUri({ scheme: 'ddp', path: 'redirect' })`를 사용하면 됩니다.

---

## 5. 동작 확인

1. 터미널에서 `npx expo start` 실행
2. 앱에서 로그인 화면으로 이동
3. **Google로 로그인** 버튼 탭
4. 브라우저(또는 인앱 웹뷰)에서 Google 계정 선택 후 허용
5. 앱으로 돌아와서 탭 화면으로 이동하면 성공

---

## 6. 문제 해결

| 증상 | 확인할 것 |
|------|------------|
| "설정 필요" 알림 | `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`가 실제로 설정되었는지, 앱을 다시 빌드/실행했는지 |
| "redirect_uri_mismatch" | Google Console의 리디렉션 URI와 앱의 `makeRedirectUri()` 결과가 **완전히 동일**한지 |
| 로그인 창이 안 뜸 | `WebBrowser.maybeCompleteAuthSession()` 호출 여부 (이미 login.tsx에 있음) |
| 테스트 시 "앱이 확인되지 않음" | OAuth 동의 화면에서 **테스트 사용자**에 해당 Google 계정 이메일 추가 |

---

## 7. (추가) 로그인 후 이메일/이름 저장

현재는 Google 로그인 성공 시 `setAuth({ email: 'google', isLoggedIn: true })`만 하고 있습니다.  
이메일·이름을 쓰려면:

1. Google 인증 후 받은 `response.params.id_token`(또는 access_token)으로  
   `https://www.googleapis.com/oauth2/v2/userinfo` 를 호출해 프로필을 가져오거나,
2. **expo-auth-session**의 `exchangeCodeAsync` 등으로 토큰을 교환한 뒤, 위 userinfo API를 호출해  
   `email`, `name`, `picture` 등을 받아서  
   `setAuth({ email: profile.email, isLoggedIn: true, nickname: profile.name })` 처럼 저장하면 됩니다.

원하면 이 부분도 코드 예시로 정리해 줄 수 있습니다.
