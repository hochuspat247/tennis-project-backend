from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
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
from app.db.models import User as UserModel
from app.db.models import Booking as BookingModel
from datetime import datetime, time
from zoneinfo import ZoneInfo  # Для работы с часовыми поясами (Python 3.9+)

router = APIRouter(prefix="/bookings", tags=["bookings"])

def force_msk(dt: datetime) -> datetime:
    """
    Преобразует dt таким образом, чтобы игнорировать tzinfo и воспринимать время как заданное в МСК.
    Например, если dt содержит 08:00 UTC, то результат будет 08:00 (наивное значение), которое мы трактуем как МСК.
    """
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

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
    try:
        # Получаем бронирования для указанного корта и даты
        bookings = (
            db.query(BookingModel)
            .options(joinedload(BookingModel.user))
            .filter(
                BookingModel.court_id == court_id,
                func.date(BookingModel.start_time) == parsed_date,
                BookingModel.status == "active"
            )
            .all()
        )
        print(f"Найденные бронирования для court_id={court_id}, date={date}: "
              f"{[(b.start_time, b.end_time) for b in bookings]}")
    except Exception as e:
        print(f"‼️ Ошибка при запросе к базе: {e}")
        raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")
    
    start_hour = 8
    end_hour = 22
    slots: List[BookingAvailability] = []
    # Определяем московский часовой пояс
    msk_tz = ZoneInfo("Europe/Moscow")
    
    for hour in range(start_hour, end_hour):
        # Формируем слот в МСК для отображения
        local_start = datetime.combine(parsed_date, time(hour, 0), tzinfo=msk_tz)
        local_end = datetime.combine(parsed_date, time(hour + 1, 0), tzinfo=msk_tz)
        slot_booked = False
        user_name = None

        for booking in bookings:
            # Если время в записи наивное, считаем, что оно в МСК, иначе преобразуем в МСК
            booking_start = booking.start_time if booking.start_time.tzinfo else booking.start_time.replace(tzinfo=msk_tz)
            booking_end = booking.end_time if booking.end_time.tzinfo else booking.end_time.replace(tzinfo=msk_tz)

            if booking_start < local_end and booking_end > local_start:
                slot_booked = True
                if user.role == "admin" and booking.user:
                    try:
                        user_name = f"{booking.user.first_name} {booking.user.last_name}"
                    except Exception as e:
                        print(f"⚠️ Ошибка при получении имени пользователя: {e}")
                        user_name = "Неизвестный"
                break

        slot = BookingAvailability(
            start=local_start.strftime("%H:%M"),
            end=local_end.strftime("%H:%M"),
            is_booked=slot_booked,
            name=user_name
        )
        slots.append(slot)
    return slots

@router.post("/", response_model=Booking)
def create_new_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    # Приводим входящие даты к МСК: независимо от tzinfo – всегда используем force_msk
    booking.start_time = force_msk(booking.start_time)
    booking.end_time = force_msk(booking.end_time)
    try:
        return create_booking(db, booking, current_user.id, current_user.role == "admin")
    except Exception as e:
        print(f"Error creating booking: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid booking data: {str(e)}")

@router.get("/my", response_model=List[Booking])
def get_my_bookings(
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    target_user_id = user_id if user_id else current_user.id
    if target_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions to view these bookings")
    return get_bookings_by_user(db, target_user_id)

@router.get("/all", response_model=List[Booking])
def get_all_bookings_admin(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    bookings = get_all_bookings(db)
    return [
        Booking.from_orm(b).dict() | {"user_name": f"{b.user.first_name} {b.user.last_name[0]}."}
        for b in bookings
    ]

@router.get("/filter", response_model=List[Booking])
def filter_bookings_endpoint(
    date_from: str,
    date_to: str,
    court: str = None,
    user_ids: List[int] = Query([]),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
):
    bookings = filter_bookings(db, date_from, date_to, court, user_ids)
    return [
        Booking.from_orm(b).dict() | {"user_name": f"{b.user.first_name} {b.user.last_name[0]}."}
        for b in bookings
    ]

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
        Booking.from_orm(booking).dict()
        | {"user_name": f"{booking.user.first_name} {booking.user.last_name[0]}."}
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
