# # test_models.py (프로젝트 루트에 생성)
# from datetime import date, timedelta, datetime, timezone
# from ddp_backend.core.database import engine, Base, SessionLocal
# from ddp_backend.models import User, Token
# from ddp_backend.schemas.enums import LoginMethod

# # # 1. 테이블 생성
# # Base.metadata.drop_all(bind=engine)
# # Base.metadata.create_all(bind=engine)
# # print("✅ 테이블 생성 완료")

# db = SessionLocal()

# # try:
# #     # 2. 유저 생성 (자체 로그인)
# #     user = User(
# #         email="test@test.com",
# #         login_method=LoginMethod.local,
# #         hashed_password="hashed_pw",
# #         name="테스터",
# #         nickname="tester",
# #         birth=date(1995, 1, 1),
# #         profile_image=None,
# #         affiliation=None,
# #     )
# #     db.add(user)
# #     db.commit()
# #     db.refresh(user)
# #     print(f"✅ 유저 생성: {user.user_id}")

# #     # 3. 토큰 생성
# #     token = Token(
# #         user_id=user.user_id,
# #         refresh_token="test_refresh_token",
# #         expires_at=datetime.now(timezone.utc) + timedelta(days=7),
# #     )
    
# #     db.add(token)
# #     db.commit()
# #     print(f"✅ 토큰 생성: {token.token_id}")

# #     # 4. OAuth 유저 생성 (hashed_password 없이)
# #     oauth_user = User(
# #         email="oauth@test.com",
# #         login_method=LoginMethod.google,
# #         hashed_password=None,  # 이게 터지면 nullable 문제
# #         name="구글유저",
# #         nickname="googleuser",
# #         birth=date(1995, 1, 1),
# #     )
# #     db.add(oauth_user)
# #     db.commit()

# #     # 4. 토큰 
# #     oauth_token = Token(
# #     user_id=oauth_user.user_id,
# #     refresh_token="oauth_refresh_token",
# #     expires_at=datetime.now(timezone.utc) + timedelta(days=7),
# #     )

# #     db.add(oauth_token)  # 이것도 빠져있었음
# #     db.commit()
# #     print(f"✅ OAuth 유저 생성: {oauth_user.user_id}")

# # except Exception as e:
# #     print(f"❌ 오류: {e}")
# #     db.rollback()
# # finally:
# #     # # 테스트 데이터 정리
# #     db.close()

# from ddp_backend.models import User, Token, Video, Source
# from ddp_backend.schemas.enums import LoginMethod, OriginPath

# # # 기존 유저 재사용 (이미 생성된 user_id=1)
# user = db.query(User).filter(User.email == "test@test.com").first()

# # # 5. Video 생성
# # video = Video(
# #     user_id=user.user_id,
# #     origin_path=OriginPath.upload,  # enum 값 확인 필요
# #     source_url="https://test.com/video.mp4",
# # )
# # db.add(video)
# # db.commit()
# # db.refresh(video)
# # print(f"✅ 비디오 생성: {video.video_id}, 상태: {video.status}")

# # # 6. Source 생성
# # source = Source(
# #     video_id=video.video_id,
# #     s3_path="s3://bucket/test/video.mp4",
# #     expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
# # )
# # db.add(source)
# # db.commit()
# # db.refresh(source)
# # print(f"✅ 소스 생성: {source.source_id}")

# from ddp_backend.models import Result, FastReport, DeepReport
# from ddp_backend.schemas.enums import Result as ResultEnum, STTRiskLevel
# from ddp_backend.schemas.report import STTScript

# video = db.query(Video).filter(Video.user_id == user.user_id).first()

# # 7. Result 생성
# result = Result(
#     user_id=user.user_id,
#     video_id=video.video_id,
#     is_fast=True,
#     is_fake=False,
# )
# db.add(result)
# db.commit()
# db.refresh(result)
# print(f"✅ Result 생성: {result.result_id}")

# # 8. FastReport 생성
# stt_script = STTScript(
#     keywords=["테스트", "키워드"],
#     risk_reason="위험 없음",
#     transcript="안녕하세요 테스트입니다",
#     search_results=[{"title": "테스트", "url": "https://test.com"}],
# )
# fast_report = FastReport(
#     user_id=user.user_id,
#     result_id=result.result_id,
#     freq_result=ResultEnum.REAL,
#     freq_conf=0.95,
#     freq_image="s3://bucket/freq.png",
#     rppg_result=ResultEnum.REAL,
#     rppg_conf=0.92,
#     rppg_image="s3://bucket/rppg.png",
#     stt_risk_level=STTRiskLevel.low,
#     stt_script=stt_script,
# )
# db.add(fast_report)
# db.commit()
# db.refresh(fast_report)
# print(f"✅ FastReport 생성: {fast_report.fast_id}")

# # 9. DeepReport 생성
# deep_report = DeepReport(
#     user_id=user.user_id,
#     result_id=result.result_id,
#     unite_result=ResultEnum.REAL,
#     unite_conf=0.93,
# )
# db.add(deep_report)
# db.commit()
# db.refresh(deep_report)
# print(f"✅ DeepReport 생성: {deep_report.deep_id}")

# from ddp_backend.models import Alert

# # 10. Alert 생성 (result와 연결)
# alert = Alert(
#     user_id=user.user_id,
#     result_id=result.result_id,
# )
# db.add(alert)
# db.commit()
# db.refresh(alert)
# print(f"✅ Alert 생성 (result 연결): {alert.alert_id}")

# # 11. Alert 생성 (result 없이 - nullable 테스트)
# alert_no_result = Alert(
#     user_id=user.user_id,
#     result_id=None,
# )
# db.add(alert_no_result)
# db.commit()
# db.refresh(alert_no_result)
# print(f"✅ Alert 생성 (result 없음): {alert_no_result.alert_id}")



# test_main.py
import httpx

BASE_URL = "http://localhost:8000"

# 1. 이메일 중복 확인
res = httpx.post(f"{BASE_URL}/user/check-email", json={"email": "test@test.com"})
print(f"✅ 이메일 중복 확인: {res.json()}")

# 2. 닉네임 중복 확인
res = httpx.post(f"{BASE_URL}/user/check-nickname", json={"nickname": "tester"})
print(f"✅ 닉네임 중복 확인: {res.json()}")

# 3. 회원가입
res = httpx.post(f"{BASE_URL}/user/register", json={
    "email": "test@test.com",
    "password": "password123",
    "name": "테스터",
    "nickname": "tester",
    "birth": "1995-01-01",
})
print(f"✅ 회원가입: {res.json()}")

# 4. 로그인
res = httpx.post(f"{BASE_URL}/auth/login", json={
    "email": "test@test.com",
    "password": "password123",
})
data = res.json()
print(f"✅ 로그인: {data}")
access_token = data.get("access_token")
refresh_token = data.get("refresh_token")

# 5. 토큰 갱신
res = httpx.post(
    f"{BASE_URL}/auth/reissue",
    headers={"Authorization": f"Bearer {refresh_token}"}
)
print(f"✅ 토큰 갱신: {res.json()}")

# 6. 회원정보 수정
res = httpx.patch(
    f"{BASE_URL}/user/edit",
    json={"new_affiliation": "개인"},
    headers={"Authorization": f"Bearer {access_token}"}
)
print(f"✅ 회원정보 수정: {res.json()}")

# 7. 로그아웃
res = httpx.post(
    f"{BASE_URL}/auth/logout",
    headers={"Authorization": f"Bearer {refresh_token}"}
)
print(f"✅ 로그아웃: {res.json()}")