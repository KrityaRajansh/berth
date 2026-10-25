import re
import uuid
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from app.models.enums import Role
from app.schemas.common import Schema

FullName = Annotated[str, Field(min_length=2, max_length=100)]
Mobile = Annotated[str, Field(pattern=r"^[6-9]\d{9}$", description="10-digit Indian mobile number")]


def check_password_strength(password: str) -> str:
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password must contain at least one letter and one digit.")
    return password


class RegisterRequest(Schema):
    full_name: FullName
    email: EmailStr
    mobile: Mobile
    password: str = Field(min_length=8, max_length=64)

    _strength = field_validator("password")(check_password_strength)


class LoginRequest(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class ProfileUpdate(Schema):
    full_name: FullName | None = None
    mobile: Mobile | None = None


class PasswordChange(Schema):
    current_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)

    _strength = field_validator("new_password")(check_password_strength)


class UserOut(Schema):
    id: uuid.UUID
    full_name: str
    email: str
    mobile: str
    role: Role
