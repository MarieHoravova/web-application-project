from pydantic import BaseModel, Field


class ReservationCreate(BaseModel):
    user_id: int = Field(...)
    code: str = Field(..., min_length=3)
    status_id: int = Field(...)

class Reservation(ReservationCreate):
    id: int
    created_at: str

    class Config:
        from_attributes = True
