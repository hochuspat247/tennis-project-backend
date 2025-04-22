from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.schemas.booking import Booking, BookingCreate, BookingAvailability
from app.services.booking_service import (
    create_booking,
    get_bookings_by_user,
    get_all_bookings,
    get_booking_by_id,
    delete_booking,
    filter_bookings,
)
from app.db.session import get_db
from app.dependencies import get_current_active_user, get_current_admin
from app.db.models import User as UserModel, Court
from app.db.models import Booking as BookingModel
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/bookings", tags=["bookings"])

def force_msk(dt: datetime) -> datetime:
    """
    Конвертирует время в MSK, сохраняя значение как наивное (без tzinfo).
    Если dt не содержит tzinfo, предполагается, что оно уже в MSK.
    """
    msk_tz = ZoneInfo("Europe/Moscow")
    if dt.tzinfo:
        dt = dt.astimezone(msk_tz)
    return dt.replace(tzinfo=None)

@router.get("/availability", response_model=List[BookingAvailability])
def get_availability(
    court_id: int = Query(...),
    date: str = Query(...),
    user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD")

    msk_tz = ZoneInfo("Europe/Moscow")
    start_of_day = datetime.combine(parsed_date, time(0, 0), tzinfo=msk_tz)
    end_of_day = datetime.combine(parsed_date + timedelta(days=1), time(0, 0), tzinfo=msk_tz)

    try:
        bookings = (
            db.query(BookingModel)
            .options(joinedload(BookingModel.user))
            .filter(
                BookingModel.court_id == court_id,
                BookingModel.start_time < end_of_day,
                BookingModel.end_time > start_of_day,
                BookingModel.status == "active"
            )
            .all()
        )
    except Exception as e:
        print(f"‼️ Ошибка при запросе к базе: {e}")
        raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")

    slots: List[BookingAvailability] = []
    for hour in range(8, 23):
        local_start = datetime.combine(parsed_date, time(hour, 0), tzinfo=msk_tz)
        local_end = (
            datetime.combine(parsed_date + timedelta(days=1), time(0, 0), tzinfo=msk_tz)
            if hour == 23 else
            datetime.combine(parsed_date, time(hour + 1, 0), tzinfo=msk_tz)
        )

        slot_booked = False
        user_name = None

        for booking in bookings:
            booking_start = booking.start_time if booking.start_time.tzinfo else booking.start_time.replace(tzinfo=msk_tz)
            booking_end = booking.end_time if booking.end_time.tzinfo else booking.end_time.replace(tzinfo=msk_tz)

            if booking_start < local_end and booking_end > local_start:
                slot_booked = True
                if user.role == "admin" and booking.user:
                    user_name = f"{booking.user.first_name.strip()} {booking.user.last_name[0] if booking.user.last_name else ''}.".strip()
                break

        slots.append(BookingAvailability(
            start=local_start.strftime("%H:%M"),
            end=local_end.strftime("%H:%M"),
            is_booked=slot_booked,
            name=user_name
        ))

    return slots

@router.post("/", response_model=Booking)
def create_new_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    # Приводим входящие даты к МСК
    booking.start_time = force_msk(booking.start_time)
    booking.end_time = force_msk(booking.end_time)
    
    # Используем booking.user_id для админов, иначе current_user.id
    user_id = booking.user_id if current_user.role == "admin" and booking.user_id else current_user.id
    
    try:
        print(f"Создание бронирования: user_id={user_id}, current_user.id={current_user.id}, start_time={booking.start_time}, role={current_user.role}")
        db_booking = create_booking(db, booking, user_id, current_user.role == "admin")
        return Booking.from_orm(db_booking).dict() | {
            "user_name": f"{db_booking.user.first_name.strip()} {db_booking.user.last_name[0] if db_booking.user.last_name else ''}.".strip()
        }
    except Exception as e:
        print(f"Error creating booking: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid booking data: {str(e)}")

@router.get("/my", response_model=List[Booking])
def get_my_bookings(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    target_user_id = user_id if user_id and current_user.role == "admin" else current_user.id

    if target_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions to view these bookings")

    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)
    bookings = (
        db.query(BookingModel)
        .options(joinedload(BookingModel.user))
        .filter(
            BookingModel.user_id == target_user_id,
            BookingModel.end_time > now,
            BookingModel.status == "active"
        )
        .all()
    )

    return [
        Booking.from_orm(b).dict() | {
            "user_name": f"{b.user.first_name.strip()} {b.user.last_name[0] if b.user.last_name else ''}.".strip()
        }
        for b in bookings
    ]

@router.get("/all", response_model=List[Booking])
def get_all_bookings_admin(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    bookings = get_all_bookings(db)
    return [
        Booking.from_orm(b).dict() | {
            "user_name": f"{b.user.first_name.strip()} {b.user.last_name[0] if b.user.last_name else ''}.".strip()
        }
        for b in bookings
    ]

@router.get("/filter", response_model=List[Booking])
def filter_bookings_endpoint(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    court: Optional[str] = Query(None),
    user_ids: Optional[List[int]] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    print(f"Получены параметры: date_from={date_from}, date_to={date_to}, court={court}, user_ids={user_ids}")
    
    # Конвертируем date_from и date_to в datetime, если они переданы
    parsed_date_from = None
    parsed_date_to = None
    try:
        if date_from:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d")
            parsed_date_from = force_msk(parsed_date_from)
        if date_to:
            parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d")
            # Устанавливаем конец дня (23:59:59) для date_to
            parsed_date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            parsed_date_to = force_msk(parsed_date_to)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        bookings = filter_bookings(db, parsed_date_from, parsed_date_to, court, user_ids)
        print(f"SQL query: {str(db.query(BookingModel).options(joinedload(BookingModel.user)))}")
        return [
            Booking.from_orm(b).dict() | {
                "user_name": f"{b.user.first_name.strip()} {b.user.last_name[0] if b.user.last_name else ''}.".strip()
            }
            for b in bookings
        ]
    except Exception as e:
        print(f"Error filtering bookings: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid filter data: {str(e)}")

@router.get("/{id}", response_model=Booking)
def get_booking(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    booking = get_booking_by_id(db, id)
    if not booking or (booking.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return (
        Booking.from_orm(booking).dict() | {
            "user_name": f"{booking.user.first_name.strip()} {booking.user.last_name[0] if booking.user.last_name else ''}.".strip()
        }
        if current_user.role == "admin"
        else Booking.from_orm(booking)
    )

@router.delete("/{id}")
def delete_booking_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    delete_booking(db, id)
    return {"status": "success", "message": "Booking deleted"}