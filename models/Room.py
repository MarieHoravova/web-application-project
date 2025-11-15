from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    number: int = Field(..., ge=1)
    room_type_id: int = Field(...)
    room_status_id: int = Field(...)
    image_path: str = Field(..., min_length=1)
    floor: int = Field(...)

class Room(RoomCreate):
    id: int

    class Config:
        from_attributes = True
