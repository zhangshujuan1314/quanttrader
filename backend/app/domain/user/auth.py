"""User model and authentication utilities."""
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models import Base
from app.config import settings

SECRET_KEY = settings.jwt_secret
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# New passwords use a deliberately slow password KDF. Existing salted SHA-256
# hashes remain readable so users can be migrated transparently on next login.
_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt via Passlib."""
    return _password_context.hash(password)


def _verify_legacy_sha256(plain: str, hashed: str) -> bool:
    """Verify the repository's legacy ``salt$sha256`` password format."""
    try:
        salt, expected = hashed.split("$", 1)
    except ValueError:
        return False
    if not salt or len(expected) != 64:
        return False
    actual = hashlib.sha256((salt + plain).encode()).hexdigest()
    return hmac.compare_digest(actual, expected)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify bcrypt hashes and legacy SHA-256 hashes during migration."""
    if hashed.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return _password_context.verify(plain, hashed)
        except (ValueError, TypeError):
            return False
    return _verify_legacy_sha256(plain, hashed)


def password_needs_rehash(hashed: str) -> bool:
    """Return True when a stored password should be upgraded after login."""
    if not hashed.startswith(("$2a$", "$2b$", "$2y$")):
        return True
    try:
        return _password_context.needs_update(hashed)
    except (ValueError, TypeError):
        return True


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
