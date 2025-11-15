from pydantic import BaseModel, Field
from typing import Optional


class RoomTypeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    capacity: int = Field(..., ge=1)
    base_price: float = Field(..., ge=0)
    description: Optional[str] = None

class RoomType(RoomTypeCreate):
    id: int

    class Config:
        from_attributes = True
