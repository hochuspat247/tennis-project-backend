from sqlalchemy.orm import Session
from app.db.models import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password, create_access_token
from random import randint

def create_user(db: Session, user: UserCreate, is_admin_creator: bool = False):
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
    return db_user

def authenticate_user(db: Session, phone: str, code: str):
    user = db.query(User).filter(User.phone == phone).first()
    if not user or user.verification_code != code:
        return None
    user.verification_code = None  # Сбрасываем код после верификации
    db.commit()
    return user

def resend_verification_code(db: Session, phone: str):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.verification_code = str(randint(1000, 9999))
    db.commit()
    # Здесь можно добавить отправку SMS
    return user

def get_current_user(db: Session, token: str):
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    return db.query(User).filter(User.id == user_id).first()