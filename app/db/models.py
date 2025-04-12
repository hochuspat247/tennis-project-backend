from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    birth_date = Column(String, nullable=True)  # Формат "ДД.ММ.ГГГГ"
    phone = Column(String, unique=True, nullable=False)  # Формат "+7(XXX)XXX-XX-XX"
    hashed_password = Column(String, nullable=False)
    photo = Column(String, nullable=True)  # Base64 или URL
    role = Column(String, default="user")  # "user" или "admin"
    is_active = Column(Boolean, default=True)
    verification_code = Column(String, nullable=True)  # Код верификации
    
    bookings = relationship("Booking", back_populates="user")

class Court(Base):
    __tablename__ = "courts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    
    bookings = relationship("Booking", back_populates="court")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    court_id = Column(Integer, ForeignKey("courts.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="active")  # "active" или "canceled"
    price = Column(Integer, nullable=False)  # Цена в копейках или рублях
    
    user = relationship("User", back_populates="bookings")
    court = relationship("Court", back_populates="bookings")