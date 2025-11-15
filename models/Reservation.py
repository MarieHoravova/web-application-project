from pydantic import BaseModel, Field


class ReservationCreate(BaseModel):
    room_id: int = Field(...)
    check_in: str = Field(...)
    check_out: str = Field(...)
    adults: int = Field(..., ge=1)
    children: int = Field(..., ge=0)
    booking_id: int = Field(...)

class Reservation(ReservationCreate):
    id: int

    class Config:
        from_attributes = True
