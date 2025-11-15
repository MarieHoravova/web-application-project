from pydantic import BaseModel


class Role(BaseModel):
    id: int
    description: str

    class Config:
        from_attributes = True
