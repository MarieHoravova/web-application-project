from pydantic import BaseModel


class PaymentMethod(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
