from datetime import timedelta
from functools import cache

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import Conflict, TooManyRequests, Unauthorized
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import Role
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, PasswordChange, ProfileUpdate, RegisterRequest

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = timedelta(minutes=1)


class AuthService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.users = UserRepository(session)

    def register(self, request: RegisterRequest) -> User:
        if self.users.email_or_mobile_taken(request.email, request.mobile):
            raise Conflict(
                "An account with this e-mail or mobile number already exists.",
                code="ACCOUNT_EXISTS",
            )
        user = User(
            full_name=request.full_name,
            email=request.email.lower(),
            mobile=request.mobile,
            password_hash=hash_password(request.password),
            role=Role.PASSENGER,
        )
        self.session.add(user)
        self.session.commit()
        return user

    def login(self, request: LoginRequest) -> User:
        now = self.clock.now()
        if self.users.failed_logins_since(request.email, now - FAILED_LOGIN_WINDOW) >= (
            MAX_FAILED_LOGINS
        ):
            raise TooManyRequests("Too many failed attempts. Try again in a minute.")

        user = self.users.by_email(request.email)
        # Verify against a dummy hash when the user is unknown so timing does not reveal it.
        password_ok = verify_password(
            request.password, user.password_hash if user else _dummy_hash()
        )
        succeeded = bool(user and password_ok)
        self.users.record_login(request.email, succeeded, now)
        self.session.commit()
        if not succeeded:
            raise Unauthorized("Incorrect e-mail or password.", code="INVALID_CREDENTIALS")
        assert user is not None
        return user

    def update_profile(self, user: User, request: ProfileUpdate) -> User:
        if request.mobile and self.users.mobile_taken_by_other(request.mobile, user.id):
            raise Conflict("This mobile number is used by another account.", code="MOBILE_TAKEN")
        if request.full_name:
            user.full_name = request.full_name
        if request.mobile:
            user.mobile = request.mobile
        self.session.commit()
        return user

    def change_password(self, user: User, request: PasswordChange) -> None:
        if not verify_password(request.current_password, user.password_hash):
            raise Unauthorized("Current password is incorrect.", code="INVALID_CREDENTIALS")
        user.password_hash = hash_password(request.new_password)
        self.session.commit()


@cache
def _dummy_hash() -> str:
    return hash_password("not-a-real-password-0")
