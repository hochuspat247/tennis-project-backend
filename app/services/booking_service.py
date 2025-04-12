from sqlalchemy.orm import Session
from app.db.models import Booking, Court, User
from app.schemas.booking import BookingCreate, BookingAvailability
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import List
from app.db.models import Booking as BookingModel
from zoneinfo import ZoneInfo  # Для работы с часовыми поясами

def ensure_msk(dt: datetime) -> datetime:
    """
    Приводит dt к московскому времени (MSK).
    Если dt не содержит tzinfo, считаем, что оно уже задано в МСК.
    Если tzinfo задан, переводим его в МСК.
    """
    msk_tz = ZoneInfo("Europe/Moscow")
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(msk_tz)

def force_msk(dt: datetime) -> datetime:
    """
    Игнорирует tzinfo в dt, возвращая наивное значение, которое трактуется как МСК.
    Например, если dt имеет значение "2025-04-14T08:00:00+00:00", результат будет 2025-04-14 08:00:00 (наивное),
    даже если реальное время UTC 08:00 соответствует 11:00 MSK.
    """
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

def create_booking(db: Session, booking: BookingCreate, user_id: int, is_admin: bool):
    print(f"Полученные данные бронирования: {booking.dict()}")
    # Приводим входящие даты к МСК, игнорируя tzinfo – всегда интерпретируем значения как МСК.
    booking.start_time = force_msk(booking.start_time)
    booking.end_time = force_msk(booking.end_time)

    start_naive = booking.start_time  # уже наивное значение, представляющее МСК
    end_naive = booking.end_time

    if start_naive.date() != end_naive.date():
        raise ValueError("Бронирование не может пересекать полночь. Начало и конец должны быть в одном дне")

    # Текущее время в МСК как наивное значение
    now_msk = datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)
    if start_naive <= now_msk:
        raise ValueError("Время начала бронирования должно быть в будущем")
    if end_naive <= start_naive:
        raise ValueError("Время окончания должно быть позже времени начала")

    existing_bookings = (
        db.query(BookingModel)
        .filter(
            BookingModel.court_id == booking.court_id,
            BookingModel.status == "active",
            BookingModel.start_time < end_naive,
            BookingModel.end_time > start_naive
        )
        .all()
    )
    existing_bookings_naive = [
        (b.start_time.replace(tzinfo=None), b.end_time.replace(tzinfo=None))
        for b in existing_bookings
    ]
    print(f"Проверка доступности для court_id={booking.court_id}, start_time={start_naive}, end_time={end_naive}")
    print(f"Существующие бронирования: {existing_bookings_naive}")

    if any(s < end_naive and e > start_naive for s, e in existing_bookings_naive):
        raise ValueError("Выбранный слот уже занят")

    db_booking = BookingModel(
        court_id=booking.court_id,
        user_id=user_id,
        start_time=start_naive,
        end_time=end_naive,
        price=booking.price,
        status="active"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def get_bookings_by_user(db: Session, user_id: int):
    return db.query(Booking).filter(Booking.user_id == user_id).all()

def get_all_bookings(db: Session):
    return db.query(Booking).all()

def get_booking_by_id(db: Session, booking_id: int):
    return db.query(Booking).filter(Booking.id == booking_id).first()

def delete_booking(db: Session, booking_id: int):
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()

def get_availability(db: Session, court_id: int, date: str, is_admin: bool = False):
    try:
        date_obj = datetime.strptime(date, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use dd.mm.yyyy")
    
    start_of_day = date_obj.replace(hour=0, minute=0)
    end_of_day = date_obj.replace(hour=23, minute=59)
    bookings = db.query(Booking).filter(
        Booking.court_id == court_id,
        Booking.start_time >= start_of_day,
        Booking.end_time <= end_of_day,
        Booking.status == "active"
    ).all()
    
    slots = []
    current_time = start_of_day
    while current_time < end_of_day:
        slot_end = current_time + timedelta(hours=1)
        booked = any(b.start_time.replace(tzinfo=None) < slot_end and b.end_time.replace(tzinfo=None) > current_time 
                     for b in bookings)
        slot = BookingAvailability(
            start=current_time.strftime("%H:%M"),
            end=slot_end.strftime("%H:%M"),
            is_booked=booked,
            name=next((b.user.first_name + " " + b.user.last_name[0] + "."
                       for b in bookings if b.start_time.replace(tzinfo=None) < slot_end and b.end_time.replace(tzinfo=None) > current_time), None) if booked and is_admin else None
        )
        slots.append(slot)
        current_time = slot_end
    return slots

def filter_bookings(db: Session, date_from: str, date_to: str, court: str, user_ids: List[int]):
    try:
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    query = db.query(Booking).join(Court).filter(
        Booking.start_time >= date_from_obj,
        Booking.end_time <= date_to_obj
    )
    if court:
        query = query.filter(Court.name == court)
    if user_ids:
        query = query.filter(Booking.user_id.in_(user_ids))
    return query.all()
