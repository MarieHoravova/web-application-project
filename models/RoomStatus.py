from pydantic import BaseModel


class RoomStatus(BaseModel):
    id: int
    description: str

    class Config:
        from_attributes = True
