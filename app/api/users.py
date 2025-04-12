from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user import User
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.db.models import User as UserModel
from typing import List  # Добавляем импорт List

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[User])
def get_all_users(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_admin)):
    return db.query(UserModel).all()