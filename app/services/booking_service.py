from sqlalchemy.orm import Session
from app.db.models import Booking as BookingModel, Court, User
from app.schemas.booking import BookingCreate, BookingAvailability
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from zoneinfo import ZoneInfo

def force_msk(dt: datetime) -> datetime:
    """
    Конвертирует время в MSK, сохраняя значение как наивное (без tzinfo).
    Если dt не содержит tzinfo, предполагается, что оно уже в MSK.
    """
    msk_tz = ZoneInfo("Europe/Moscow")
    if dt.tzinfo:
        dt = dt.astimezone(msk_tz)
    return dt.replace(tzinfo=None)

def create_booking(db: Session, booking: BookingCreate, user_id: int, is_admin: bool) -> BookingModel:
    print(f"Полученные данные бронирования: {booking.dict()}")
    # Приводим входящие даты к МСК, игнорируя tzinfo
    booking.start_time = force_msk(booking.start_time)
    booking.end_time = force_msk(booking.end_time)

    start_naive = booking.start_time
    end_naive = booking.end_time

    if start_naive.date() != end_naive.date():
        raise ValueError("Бронирование не может пересекать полночь. Начало и конец должны быть в одном дне")

    # Текущее время в МСК как наивное значение
    now_msk = datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)
    if start_naive <= now_msk:
        raise ValueError("Время начала бронирования должно быть в будущем")
    if end_naive <= start_naive:
        raise ValueError("Время окончания должно быть позже времени начала")

    # Проверка существующих бронирований
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

def get_bookings_by_user(db: Session, user_id: int) -> List[BookingModel]:
    return db.query(BookingModel).filter(BookingModel.user_id == user_id).all()

def get_all_bookings(db: Session) -> List[BookingModel]:
    return db.query(BookingModel).options(joinedload(BookingModel.user)).all()

def get_booking_by_id(db: Session, booking_id: int) -> Optional[BookingModel]:
    return db.query(BookingModel).options(joinedload(BookingModel.user)).filter(BookingModel.id == booking_id).first()

def delete_booking(db: Session, booking_id: int):
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()

def filter_bookings(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    court: Optional[str] = None,
    user_ids: Optional[List[int]] = None
) -> List[BookingModel]:
    query = db.query(BookingModel).options(joinedload(BookingModel.user))
    
    if date_from:
        query = query.filter(BookingModel.start_time >= date_from)
    if date_to:
        query = query.filter(BookingModel.end_time <= date_to)
    if court:
        query = query.join(Court).filter(Court.name == court)
    if user_ids and len(user_ids) > 0:
        query = query.filter(BookingModel.user_id.in_(user_ids))
    
    bookings = query.all()
    print(f"Filtered bookings: {len(bookings)} bookings found for user_ids={user_ids}, court={court}")
    print(f"SQL query: {str(query)}")
    return bookings

def get_availability(db: Session, court_id: int, date: str, is_admin: bool = False) -> List[BookingAvailability]:
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    start_of_day = date_obj.replace(hour=0, minute=0)
    end_of_day = date_obj.replace(hour=23, minute=59)
    bookings = db.query(BookingModel).options(joinedload(BookingModel.user)).filter(
        BookingModel.court_id == court_id,
        BookingModel.start_time >= start_of_day,
        BookingModel.end_time <= end_of_day,
        BookingModel.status == "active"
    ).all()
    
    slots = []
    current_time = start_of_day
    while current_time < end_of_day:
        slot_end = current_time + timedelta(hours=1)
        booked = any(
            b.start_time.replace(tzinfo=None) < slot_end and b.end_time.replace(tzinfo=None) > current_time 
            for b in bookings
        )
        slot = BookingAvailability(
            start=current_time.strftime("%H:%M"),
            end=slot_end.strftime("%H:%M"),
            is_booked=booked,
            name=next(
                (f"{b.user.first_name.strip()} {b.user.last_name[0] if b.user.last_name else ''}.".strip()
                 for b in bookings
                 if b.start_time.replace(tzinfo=None) < slot_end and b.end_time.replace(tzinfo=None) > current_time),
                None
            ) if booked and is_admin else None
        )
        slots.append(slot)
        current_time = slot_end
    return slots