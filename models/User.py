from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    phone_number: Optional[str] = None
    role_id: int = Field(...)

class UserPublic(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role_id: int
    created_at: str

    class Config:
        from_attributes = True
