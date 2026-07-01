from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.sms import router as sms_router
from api.v1.categories import router as categories_router
from api.v1.transaction import router as transactions_router
from api.v1.dashboard import router as dashboard_router
from api.v1.user import router as user_router

# Central router — all v1 sub-routers attach here
index_router = APIRouter(prefix="/api/v1")

index_router.include_router(auth_router)
index_router.include_router(sms_router)
index_router.include_router(categories_router)
index_router.include_router(transactions_router)
index_router.include_router(dashboard_router)
index_router.include_router(user_router)

