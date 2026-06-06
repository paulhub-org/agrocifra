"""Зависимости FastAPI: текущий пользователь и контроль доступа по ролям (Спринт 4)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.models import Role, UserAccount

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserAccount:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        login = payload.get("sub")
        if not login:
            raise cred_exc
    except JWTError as exc:
        raise cred_exc from exc
    user = db.execute(
        select(UserAccount).where(UserAccount.login == login)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise cred_exc
    return user


def scope_filters(user: UserAccount) -> tuple[int | None, int | None, str | None]:
    """(org_id, region_id, district) для ограничения выборок по роли.

    organization → своя организация; regional_operator → своя область;
    district_operator → своя область и район; digitalization_office и
    state_authority → без ограничения (None, None, None).
    """
    if user.role == Role.organization.value:
        return user.organization_id, None, None
    if user.role == Role.regional_operator.value:
        return None, user.region_id, None
    if user.role == Role.district_operator.value:
        return None, user.region_id, user.district
    return None, None, None


def require_roles(*roles: Role | str):
    """Зависимость: допускает только пользователей с одной из перечисленных ролей."""
    allowed = {r.value if isinstance(r, Role) else r for r in roles}

    def checker(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        return user

    return checker
