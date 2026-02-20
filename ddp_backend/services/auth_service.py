# services/auth_service.py (비즈니스 로직)
# 학생님이 가장 집중해야 할 **'알맹이'**입니다.

# 정의: DB 세션을 열어 사용자가 있는지 확인하고, 비밀번호를 검증한 뒤 결과를 반환하는 실제 로직을 짭니다.

# 실제 적용: create_user, authenticate_user 함수를 이곳에 구현합니다.

# def authenticate_user(db, email, password):
#     # 1. DB에서 사용자 찾기
#     # 2. security.py의 함수로 비번 비교하기
#     # 3. 맞으면 토큰 생성, 틀리면 에러 반환
#     pass