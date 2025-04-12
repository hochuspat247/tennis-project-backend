from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import User, UserBase, UserUpdate
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.db.models import User as UserModel

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/{user_id}", response_model=User)
def get_profile(user_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_active_user)):
    # Проверяем, имеет ли текущий пользователь доступ к запрашиваемому профилю
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to view this profile")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user

@router.patch("/{user_id}", response_model=User)
def update_profile(
    user_id: int,
    updated_data: UserUpdate,  # заменил тут
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to edit this profile")
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user