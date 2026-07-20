from fastapi import APIRouter

from app.api.routes import (
    audit,
    chats,
    dashboard,
    documents,
    login,
    private,
    retrieval,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(chats.router)
api_router.include_router(documents.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)

api_router.include_router(retrieval.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
