from pydantic import BaseModel, field_validator
from app.schemas.client_user import ClientUserResponse
import re


def normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned.startswith("+"):
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "+7" + cleaned[1:]
        elif cleaned.startswith("7") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        else:
            cleaned = "+" + cleaned
    if len(cleaned) < 10 or len(cleaned) > 16:
        raise ValueError("Invalid phone number format. Expected format: +79991234567")
    return cleaned


class RequestCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class RequestCodeResponse(BaseModel):
    bot_url: str
    auth_token: str
    dev_code: str | None = None


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        code = v.strip()
        if not code.isdigit() or len(code) != 4:
            raise ValueError("OTP code must be 4 digits")
        return code
