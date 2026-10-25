from fastapi import APIRouter, Response, status

from app.api.deps import (
    ClockDep,
    CurrentUser,
    SessionDep,
    clear_session_cookie,
    set_session_cookie,
)
from app.core.security import create_session_token
from app.schemas.auth import LoginRequest, PasswordChange, ProfileUpdate, RegisterRequest, UserOut
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest, response: Response, session: SessionDep, clock: ClockDep
) -> UserOut:
    user = AuthService(session, clock).register(body)
    set_session_cookie(response, create_session_token(user.id, user.role, clock.now()))
    return UserOut.model_validate(user)


@router.post("/auth/login")
def login(body: LoginRequest, response: Response, session: SessionDep, clock: ClockDep) -> UserOut:
    user = AuthService(session, clock).login(body)
    set_session_cookie(response, create_session_token(user.id, user.role, clock.now()))
    return UserOut.model_validate(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/auth/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/users/me")
def update_profile(
    body: ProfileUpdate, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> UserOut:
    return UserOut.model_validate(AuthService(session, clock).update_profile(user, body))


@router.post("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> None:
    AuthService(session, clock).change_password(user, body)
