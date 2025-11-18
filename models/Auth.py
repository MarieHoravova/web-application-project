from pydantic import BaseModel, EmailStr, field_validator


def validate_password_strength(value: str) -> str:
    if len(value) < 6:
        raise ValueError("Heslo musí mít alespoň 6 znaků")
    if not any(c.isdigit() for c in value):
        raise ValueError("Heslo musí obsahovat číslici")
    if not any(c.isalpha() for c in value):
        raise ValueError("Heslo musí obsahovat písmeno")
    return value

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: str | None = None

    @field_validator("password")
    def check_password(cls, value):
        return validate_password_strength(value)

    @field_validator("phone_number")
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None

        cleaned = value.replace(" ", "")  # remove spaces

        if cleaned.startswith("+"):
            cleaned = cleaned[1:]

        if not cleaned.isdigit():
            raise ValueError("Telefonní číslo může obsahovat pouze číslice a znak '+'")

        if len(cleaned) < 9:
            raise ValueError("Telefonní číslo je příliš krátké (minimálně 9 číslic)")

        if len(cleaned) > 15:
            raise ValueError("Telefonní číslo je příliš dlouhé")

        return value


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    def check_new_password(cls, value):
        return validate_password_strength(value)