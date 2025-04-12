from pydantic import BaseModel
from typing import Optional  # Добавляем импорт Optional

class CourtBase(BaseModel):
    name: str
    description: Optional[str] = None

class CourtCreate(CourtBase):
    pass

class Court(CourtBase):
    id: int
    
    class Config:
        orm_mode = True