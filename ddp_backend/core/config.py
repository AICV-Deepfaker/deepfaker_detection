import os 
from dotenv import load_dotenv 

# .env 파일의 내용을 환경 변수로 부르기 
load_dotenv() 

# 환경 변수에서 URL을 가져와 DB 엔진 만들기 
DATABASE_URL = os.getenv("DATABASE_URL")