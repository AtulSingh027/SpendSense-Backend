import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from configs.db_config import get_db
from helpers.middelwares.auth_middelware import get_current_user
from models.category import Category
from schemas.categories import CategoryCreate, CategoryResponse, CategoryUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "/create",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom category",
)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        # Check if category with this name already exists as a system category or for this user
        existing = db.execute(
            select(Category).where(
                Category.name == body.name,
                (Category.user_id == current_user_id) | (Category.is_system == True),
            )
        ).scalars().first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )

        new_category = Category(
            name=body.name,
            icon=body.icon,
            user_id=current_user_id,
            is_system=False,
        )

        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Category creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category creation failed",
        )


@router.get(
    "/",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all readable categories",
)
def get_all_categories(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        # Return all categories that are either system categories or custom to this user
        categories = db.execute(
            select(Category).where(
                (Category.user_id == current_user_id) | (Category.is_system == True)
            )
        ).scalars().all()
        return categories
    except Exception as e:
        logger.exception("Category retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category retrieval failed",
        )


@router.get(
    "/{id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get category by ID",
)
def get_category_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        category = db.execute(
            select(Category).where(Category.id == id)
        ).scalars().first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Check authorization: user can only view their own custom categories or system categories
        if not category.is_system and category.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this category",
            )

        return category

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Category retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category retrieval failed",
        )


@router.put(
    "/{id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a custom category",
)
def update_category(
    id: int,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        category = db.execute(
            select(Category).where(Category.id == id)
        ).scalars().first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system categories",
            )

        if category.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this category",
            )

        # If name is being updated, verify it doesn't conflict with another category name
        if body.name is not None and body.name != category.name:
            existing = db.execute(
                select(Category).where(
                    Category.name == body.name,
                    (Category.user_id == current_user_id) | (Category.is_system == True),
                )
            ).scalars().first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category with this name already exists",
                )
            category.name = body.name

        if body.icon is not None:
            category.icon = body.icon

        db.commit()
        db.refresh(category)
        return category

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Category update failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category update failed",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a custom category",
)
def delete_category(
    id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    try:
        category = db.execute(
            select(Category).where(Category.id == id)
        ).scalars().first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system categories",
            )

        if category.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this category",
            )

        db.delete(category)
        db.commit()
        return {"success": True, "message": "Category deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Category deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category deletion failed",
        )
