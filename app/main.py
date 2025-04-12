from fastapi import FastAPI
from app.api import auth, bookings, users, courts, profile
from app.db.base import Base
from app.db.session import engine

app = FastAPI(title="Tennis Project API")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(courts.router, prefix="/api")
app.include_router(profile.router, prefix="/api")