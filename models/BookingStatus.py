from pydantic import BaseModel


class BookingStatus(BaseModel):
    id: int
    description: str

    class Config:
        from_attributes = True
