from typing import List  # Добавляем импорт
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.court import Court, CourtCreate
from app.db.session import get_db
from app.db.models import Court as CourtModel

router = APIRouter(prefix="/courts", tags=["courts"])

@router.post("/", response_model=Court)
def create_court(court: CourtCreate, db: Session = Depends(get_db)):
    db_court = CourtModel(**court.dict())
    db.add(db_court)
    db.commit()
    db.refresh(db_court)
    return db_court

@router.get("/", response_model=List[Court])
def get_courts(db: Session = Depends(get_db)):
    return db.query(CourtModel).all()