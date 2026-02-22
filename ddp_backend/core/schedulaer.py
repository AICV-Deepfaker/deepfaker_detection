from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta

from core.database import SessionLocal # DB에서 직접 처리
from models.models import Token 

def revoke_expired_tokens():
    """30일 이상 미사용 토큰 revoked=True 처리"""
    db = SessionLocal()
    try:
        expired = datetime.now(timezone.utc)

        db.query(Token)\
            .filter(Token.revoked == False)\
            .filter(Token.expires_at < expired)\
            .update({Token.revoked: True}, synchronize_session=False)
        db.commit()
    finally:
        db.close()

scheduler = BackgroundScheduler()

def start_schedular():
    if not scheduler.running:
        scheduler.add_job(
            revoke_expired_tokens,
            trigger='cron',
            hour=0, # 매일 자정 실행
            id="revoke_job",
            replace_existing=True # 같은 id 존재시 덮어씌움
        )
    scheduler.start()

def shutdown_schedular():
    if scheduler.running:
        scheduler.shutdown()