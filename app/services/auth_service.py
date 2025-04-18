from sqlalchemy.orm import Session
from app.db.models import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from random import randint
from fastapi import HTTPException
from app.utils.sms import send_sms
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_user(db: Session, user: UserCreate, is_admin_creator: bool = False):
    if user.is_admin and not is_admin_creator:
        raise HTTPException(status_code=403, detail="Only admin can create admins")
    
    existing_user = db.query(User).filter((User.email == user.email) | (User.phone == user.phone)).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email or phone already registered")
    
    hashed_password = get_password_hash(user.password)
    verification_code = str(randint(1000, 9999)) if not user.is_admin else None
    db_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        birth_date=user.birth_date,
        phone=user.phone,
        hashed_password=hashed_password,
        photo=user.photo,
        role="admin" if user.is_admin else "user",
        verification_code=verification_code
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Отправляем СМС с кодом верификации, если пользователь не администратор
    if verification_code:
        try:
            await send_sms(db_user.phone, verification_code)
            logger.info(f"SMS sent to {db_user.phone} with code: {verification_code}")
        except HTTPException as e:
            logger.error(f"Failed to send SMS to {db_user.phone}: {e.detail}")
            # Продолжаем, так как код сохранен в БД
            pass

    return db_user

def authenticate_user(db: Session, phone: str, code: str):
    user = db.query(User).filter(User.phone == phone).first()
    if not user or user.verification_code != code:
        return None
    user.verification_code = None  # Сбрасываем код после верификации
    db.commit()
    return user

async def resend_verification_code(db: Session, phone: str):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.verification_code = str(randint(1000, 9999))
    db.commit()

    # Отправляем СМС с новым кодом
    try:
        await send_sms(user.phone, user.verification_code)
        logger.info(f"SMS sent to {user.phone} with code: {user.verification_code}")
    except HTTPException as e:
        logger.error(f"Failed to send SMS to {user.phone}: {e.detail}")
        raise e

    return user

def get_current_user(db: Session, token: str):
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()