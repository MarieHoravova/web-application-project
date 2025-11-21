from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    reservation_id: int = Field(...)
    amount: float = Field(..., gt=0)
    method_id: int = Field(...)

class Payment(PaymentCreate):
    id: int
    paid_at: str

    class Config:
        from_attributes = True
