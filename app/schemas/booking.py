from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class BookingBase(BaseModel):
    court_id: int
    start_time: datetime
    end_time: datetime
    price: int

class BookingCreate(BookingBase):
    user_id: Optional[int] = None  # Для администратора

class Booking(BookingBase):
    id: int
    user_id: int
    status: str
    user_name: Optional[str] = None  # Только для администратора
    
    class Config:
        orm_mode = True

class BookingAvailability(BaseModel):
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    is_booked: bool
    name: Optional[str] = None  # Только для администратора