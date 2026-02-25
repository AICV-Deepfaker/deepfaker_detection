#임시 비밀번호 이메일 발송

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ddp_backend.core.config import settings

def send_temp_pwd(to_email: str, temp_password: str): # to_email: 임시 비밀번호 전송 이메일 주소
    msg = MIMEMultipart()
    msg["From"] = settings.GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "[DDP] 임시 비밀번호 안내"

    body = f"""
    안녕하세요.
    
    임시 비밀번호: {temp_password}
    
    로그인 후 반드시 비밀번호를 변경해주세요.
    """
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        smtp.sendmail(settings.GMAIL_USER, to_email, msg.as_string())



# 이후 실사용 서비스로 전환 시 사용할 수 있는 AWS SES 가이드
#- AWS SES 사용 가이드 (IAM 사용자 · Sandbox 기준)

# 본 문서는 IAM 계정으로 AWS에 접근한 사용자가 SES(Simple Email Service)를 이용하여  
# 이메일 템플릿 생성 및 이메일 발송을 수행하는 방법을 설명합니다.  
# (Sandbox 환경 기준)

# ---

# 1. 사전 조건

# 다음 항목은 관리자에 의해 사전에 설정되어 있어야 합니다.

# - IAM 사용자 또는 Role 발급 완료
# - SES 사용 권한(IAM Policy) 부여 완료
# - 발신 이메일(From Address) Verified 상태
# - 사용 리전: us-east-2 (Ohio)

# ---

# 2. AWS 로그인 및 리전 확인

# AWS Console 로그인 후 우측 상단 리전을 확인합니다.

# ```
# us-east-2 (Ohio)
# ```

# SES는 리전 단위 서비스이므로 반드시 동일한 리전을 사용해야 합니다.

# ---

# 3. Sandbox 환경에서 수신자 등록

# Sandbox 환경에서는 이메일을 수신하는 주소(To Address) 역시  
# 사전에 등록(Verify)되어야 합니다.

# 경로

# ```
# Amazon SES → Configuration → Identities → Create identity
# ```

# 설정

# - Identity type: Email address
# - 수신 테스트용 이메일 입력

# 등록 후 해당 이메일로 Verification 메일이 발송됩니다.

# 수신자가 메일 내 Verify 링크를 클릭하면 등록이 완료됩니다.

# 정상 등록 상태

# ```
# Verified
# ```

# ---

# 4. 이메일 템플릿 생성

# 콘솔 UI에서 Create 버튼이 보이지 않는 경우  
# AWS CloudShell을 이용하여 생성합니다.

# CloudShell 실행  
# AWS Console 하단의 CloudShell 실행

# 템플릿 생성

# ```bash
# aws sesv2 create-email-template \
#   --template-name temporary_password_template \
#   --template-content '{
#     "Subject":"임시 비밀번호 안내",
#     "Text":"임시 비밀번호: {{temp_password}}",
#     "Html":"<h2>임시 비밀번호 안내</h2><b>{{temp_password}}</b>"
#   }'
# ```

# 생성 확인

# ```bash
# aws sesv2 list-email-templates
# ```

# 템플릿 목록에 TemplateName이 표시되면 정상입니다.

# ---

# 5. 템플릿 렌더링 테스트

# 변수 치환이 정상적으로 동작하는지 확인합니다.

# ```bash
# aws sesv2 test-render-email-template \
#   --template-name temporary_password_template \
#   --template-data '{"temp_password":"A1B2C3"}'
# ```

# 출력 결과에 값이 치환되어 나타나면 정상입니다.

# ---

# 6. 이메일 발송

# 템플릿 기반 이메일 발송 예시입니다.

# ```bash
# aws sesv2 send-email \
#   --from-email-address "researcherhojin@gmail.com" \
#   --destination "ToAddresses=tester@gmail.com" \
#   --content '{
#     "Template":{
#       "TemplateName":"temporary_password_template",
#       "TemplateData":"{\"temp_password\":\"A1B2C3\"}"
#     }
#   }'
# ```

# 성공 시 MessageId가 반환됩니다.

# 메일은 Inbox 또는 Spam 폴더로 수신될 수 있습니다.

# ---

# 7. Sandbox 환경 제한 사항

# 현재 SES 계정이 Sandbox 상태일 경우 다음 제한이 적용됩니다.

# - Verified 된 이메일 주소로만 발송 가능
# - 하루 최대 200건 이메일 발송
# - 초당 1건 전송 제한

# 테스트 목적에서는 정상적인 동작입니다.

# ---

# 8. IAM 사용자 기준 수행 가능 작업

# IAM 권한이 부여된 사용자는 다음 작업을 수행할 수 있습니다.

# - 수신 이메일 등록 (Identity 생성)
# - 이메일 템플릿 생성 및 조회
# - 템플릿 렌더 테스트
# - 이메일 발송

# ---

# 9. 기본 사용 흐름

# IAM 사용자 기준 실제 사용 순서는 다음과 같습니다.

# 1. 수신자 이메일 등록 및 Verify
# 2. 이메일 템플릿 생성
# 3. 템플릿 렌더링 테스트
# 4. send-email 명령으로 이메일 발송

# ---

# 10. 참고 사항

# - SES는 리전별 리소스로 관리됩니다.
# - Sandbox 환경에서는 운영 서비스 사용이 제한됩니다.
# - 운영 환경에서는 Production Access 승인이 필요합니다.
# - CloudShell 사용 시 별도 AWS CLI 설치는 필요하지 않습니다.