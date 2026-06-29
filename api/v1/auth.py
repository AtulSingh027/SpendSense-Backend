from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from configs.db_config import get_db
from schemas.user import AuthResponse, UserCreate, UserResponse,UserLogin
from services.auth_service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    """Create a new user with phone + password and return an access token."""
    try:
        user, token = register_user(
            db=db,
            phone_number=body.phone_number,
            password=body.password,
            full_name=body.full_name,
            email=body.email,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )



@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login a user",
)
def login(body : UserLogin, db : Session = Depends(get_db)):
    """Login a user and return an access token"""
    try:
        user, token = login_user(
            db=db,
            phone_number=body.phone_number,
            password=body.password,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )

