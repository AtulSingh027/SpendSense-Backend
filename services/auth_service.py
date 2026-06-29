from sqlalchemy import select
from sqlalchemy.orm import Session

from helpers.middelwares.auth_middelware import create_access_token, hash_password,verify_password
from models.user import User


def register_user(db: Session, phone_number: str, password: str, full_name: str | None, email: str | None) -> tuple[User, str]:
    """
    Create a new user with a hashed password and return (user, access_token).
    Raises ValueError if the phone number is already registered.
    """
    existing = db.execute(
        select(User).where(User.phone_number == phone_number)
    ).scalar_one_or_none()

    if existing is not None:
        raise ValueError("Phone number already registered")

    user = User(
        phone_number=phone_number,
        password_hash=hash_password(password),
        full_name=full_name,
        email=email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"user_id": user.id})
    return user, token


def login_user(
    db: Session,
    phone_number: str,
    password: str,
) -> tuple[User, str]:
    """
    Verify credentials and return (user, access_token).  
    Raises ValueError if the user is not found or password is incorrect.
    """
    user = db.execute(
        select(User).where(User.phone_number == phone_number)
    ).scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid credentials")

    token = create_access_token({"user_id": user.id})
    return user, token
