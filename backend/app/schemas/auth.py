"""Схемы аутентификации и пользователей (Спринт 4)."""
from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    login: str
    full_name: str | None
    role: str
    organization_id: int | None
    region_id: int | None


class UserCreate(BaseModel):
    login: str
    password: str
    role: str = "organization"
    full_name: str | None = None
    email: str | None = None
    organization_id: int | None = None
    region_id: int | None = None
