from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    birth_date: Optional[str] = Field(None, pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    phone: str = Field(..., pattern=r"^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$")
    photo: Optional[str] = None

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    role: str
    is_active: bool
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: str  # Добавляем refresh_token
    token_type: str
    role: str
    user_id: int
    expires_in: Optional[int] = None  # Добавляем expires_in (опционально)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = Field(None, pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    phone: Optional[str] = None
    photo: Optional[str] = None