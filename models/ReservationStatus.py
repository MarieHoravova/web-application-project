from pydantic import BaseModel


class ReservationStatus(BaseModel):
    id: int
    description: str

    class Config:
        from_attributes = True
