from pydantic import BaseModel, Field


class ReservationItemCreate(BaseModel):
    room_id: int = Field(...)
    check_in: str = Field(...)
    check_out: str = Field(...)
    adults: int = Field(..., ge=1)
    children: int = Field(..., ge=0)
    reservation_id: int = Field(...)

class ReservationItem(ReservationItemCreate):
    id: int

    class Config:
        from_attributes = True
