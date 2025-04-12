from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, User, Token
from app.services.auth_service import create_user, authenticate_user, resend_verification_code
from app.db.session import get_db
from app.dependencies import get_current_admin, get_current_active_user
from app.db.models import User as UserModel
from app.core.security import create_access_token
from random import randint

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(phone: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Генерируем код верификации
    user.verification_code = str(randint(1000, 9999))
    db.commit()
    
    # Выводим информацию в консоль
    print(f"User login attempt: Phone: {phone}, User ID: {user.id}, Verification Code: {user.verification_code}")
    
    return {
        "status": "success",
        "message": "Verification code sent",
        "user_id": user.id
    }

@router.post("/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_active_user)):
    is_admin_creator = current_user and current_user.role == "admin"
    return create_user(db, user, is_admin_creator)

@router.post("/verify", response_model=Token)
def verify_user(phone: str, code: str, db: Session = Depends(get_db)):
    user = authenticate_user(db, phone, code)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid code")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role,"user_id": user.id}

@router.post("/resend-code")
def resend_code(phone: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    resend_verification_code(db, phone)
    
    # Выводим информацию в консоль после генерации нового кода
    user = db.query(UserModel).filter(UserModel.phone == phone).first()  # Обновляем данные пользователя
    print(f"User resend code attempt: Phone: {phone}, User ID: {user.id}, Verification Code: {user.verification_code}")
    
    return {"status": "success", "message": "Code resent"}