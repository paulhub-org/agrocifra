"""Эндпоинты аутентификации: вход (JWT) и профиль текущего пользователя (Спринт 4)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import Role, UserAccount
from app.schemas.auth import MessageOut, RegisterRequest, SwitchRoleRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

_ROLE_VALUES = {r.value for r in Role}
# Демо-учётные записи по ролям (для удобного режима «просмотр как» в пилоте)
_DEMO_LOGIN = {
    Role.organization.value: "org",
    Role.regional_operator.value: "region",
    Role.district_operator.value: "district",
    Role.digitalization_office.value: "office",
    Role.state_authority.value: "gov",
}


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


@router.post("/register", response_model=MessageOut, status_code=201,
             summary="Регистрация новой учётной записи (с подтверждением)")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.role not in _ROLE_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Недопустимая роль")
    exists = db.execute(
        select(UserAccount).where(UserAccount.login == payload.login)
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Учётная запись с таким логином уже существует")
    db.add(UserAccount(
        login=payload.login,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        email=payload.email,
        is_active=False,  # требуется подтверждение администратором
    ))
    db.commit()
    return MessageOut(message="Заявка на регистрацию отправлена и ожидает подтверждения.")


@router.get("/pending", response_model=list[UserOut],
            summary="Заявки на регистрацию, ожидающие подтверждения")
def pending_users(db: Session = Depends(get_db),
                  _user=Depends(require_roles(Role.digitalization_office, Role.state_authority))):
    return db.execute(
        select(UserAccount).where(UserAccount.is_active.is_(False)).order_by(UserAccount.id)
    ).scalars().all()


@router.post("/users/{user_id}/activate", response_model=UserOut,
             summary="Подтвердить (активировать) учётную запись")
def activate_user(user_id: int, db: Session = Depends(get_db),
                  _user=Depends(require_roles(Role.digitalization_office, Role.state_authority))):
    user = db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Учётная запись не найдена")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/switch-role", response_model=Token,
             summary="Переключение роли просмотра (только офис цифровизации)")
def switch_role(payload: SwitchRoleRequest, db: Session = Depends(get_db),
                _user=Depends(require_roles(Role.digitalization_office))):
    """Режим «просмотр как»: выдаёт токен демонстрационной учётной записи выбранной роли.

    Возврат к роли «Офис цифровизации» выполняется на стороне клиента (сохранённый токен).
    Предусмотрено для единого пилота как удобство демонстрации.
    """
    if payload.role not in _ROLE_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Недопустимая роль")
    login = _DEMO_LOGIN.get(payload.role)
    target = db.execute(
        select(UserAccount).where(UserAccount.login == login)
    ).scalar_one_or_none()
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Демонстрационная учётная запись для этой роли недоступна")
    return Token(access_token=create_access_token(target.login, target.role), role=target.role)
