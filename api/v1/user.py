from schemas.user import UserResponse, UserUpdate
from fastapi import Depends, HTTPException, status, APIRouter
from models.user import User
from configs.db_config import get_db
from helpers.middelwares.auth_middelware import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)



router = APIRouter(prefix="/user", tags=["user"])


@router.get('/{user_id}', response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_profile(
    user_id : int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this user profile",
            )
            
        user = db.execute(select(User).where(User.id == current_user_id)).scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            full_name=user.full_name,
            email=user.email,
            image_url=user.image_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("User profile retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User profile retrieval failed",
        )


@router.put('/{user_id}', response_model = UserResponse, status_code = status.HTTP_200_OK)
def update_user_profile(
    user_id : int,
    body : UserUpdate,
    current_user_id : int = Depends(get_current_user),
    db : Session = Depends(get_db),
):
    try:
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this user profile",
            )

        user = db.execute(select(User).where(User.id == current_user_id)).scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if body.full_name:
            user.full_name = body.full_name
        if body.email:
            user.email = body.email
        if body.phone_number:
            user.phone_number = body.phone_number
        if body.image_url:
            user.image_url = body.image_url

        db.commit()
        db.refresh(user)
        
        return UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            full_name=user.full_name,
            email=user.email,
            image_url=user.image_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("User profile update failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User profile update failed",
        )
