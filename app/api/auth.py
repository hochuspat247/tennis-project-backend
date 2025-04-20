from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, User, Token
from app.services.auth_service import create_user, authenticate_user, resend_verification_code
from app.db.session import get_db
from app.dependencies import get_current_admin, get_current_active_user
from app.db.models import User as UserModel
from app.core.security import create_access_token
from random import randint
from app.utils.sms import send_sms
from jose import JWTError, jwt
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Настройки JWT
SECRET_KEY = "your-secret-key"  # Замени на свой секретный ключ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login")
async def login(phone: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Генерируем код верификации
    user.verification_code = str(randint(1000, 9999))
    db.commit()
    
    # Отправляем СМС с кодом
    try:
        await send_sms(phone, user.verification_code)
        logger.info(f"User login attempt: Phone: {phone}, User ID: {user.id}, Verification Code: {user.verification_code}")
    except HTTPException as e:
        logger.error(f"Failed to send SMS to {phone}: {e.detail}")
        raise e

    return {
        "status": "success",
        "message": "Verification code sent",
        "user_id": user.id
    }

@router.post("/register", response_model=User)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    is_admin_creator = current_user and current_user.role == "admin"
    return await create_user(db, user, is_admin_creator)

@router.post("/verify", response_model=Token)
def verify_user(phone: str, code: str, db: Session = Depends(get_db)):
    user = authenticate_user(db, phone, code)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid code")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # Добавляем рефреш-токен
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Проверяем, существует ли пользователь
        user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Создаём новый access-токен
        access_token = create_access_token(data={"sub": user_id})
        return {"access_token": access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/resend-code")
async def resend_code(phone: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await resend_verification_code(db, phone)
    
    logger.info(f"User resend code attempt: Phone: {phone}, User ID: {user.id}, Verification Code: {user.verification_code}")
    
    return {"status": "success", "message": "Code resent"}