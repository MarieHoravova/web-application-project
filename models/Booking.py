from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    user_id: int = Field(...)
    code: str = Field(..., min_length=3)
    status_id: int = Field(...)

class Booking(BookingCreate):
    id: int
    created_at: str

    class Config:
        from_attributes = True
