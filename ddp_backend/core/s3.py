from pathlib import Path
# AWS s3


# =========
# User
# =========

# 프로필 이미지 업로드
def upload_image_to_s3(file, filename: str) -> str:
    pass  # 이후 개발 예정

# 프로필 이미지 삭제
def delete_image_from_s3(url: str):
    pass  # 이후 개발 예정

# 회원탈퇴 시 s3_path를 확인하여 즉각 삭제
def delete_video_from_s3(url: str):
    pass  # 이후 개발 예정

# 예외사항 반드시 넣기

def download_video_from_s3(url: str, download_path: Path) -> Path:
    return download_path
    pass