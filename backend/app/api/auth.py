"""Эндпоинты аутентификации: вход (JWT) и профиль текущего пользователя (Спринт 4)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.models import UserAccount
from app.schemas.auth import Token, UserOut

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(
        select(UserAccount).where(UserAccount.login == form.username)
    ).scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Учётная запись отключена")
    return Token(access_token=create_access_token(user.login, user.role), role=user.role)


@router.get("/me", response_model=UserOut)
def me(user: UserAccount = Depends(get_current_user)):
    return user
