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


class RegisterRequest(BaseModel):
    """Самостоятельная регистрация (учётная запись создаётся неактивной — требует подтверждения)."""
    login: str
    password: str
    role: str = "organization"
    full_name: str | None = None
    email: str | None = None


class SwitchRoleRequest(BaseModel):
    """Переключение роли просмотра (режим «просмотр как», только для офиса цифровизации)."""
    role: str


class MessageOut(BaseModel):
    message: str
