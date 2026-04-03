"""
UserRouter — Endpoints for user profile and freemium status.

## Traceability
Feature: F001 — Google OAuth Authentication, F004 — Freemium Limits
Scenarios: SC001, SC004

## Business context
The bot calls these to display the user's connection status and remaining
free syncs before prompting for payment (SC004).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.exceptions import AuthNotConnectedException
from backend.repository.user_repository import UserRepository
from backend.schema.user_schema import FreemiumStatusSchema, UserResponseSchema
from backend.service.freemium_service import FreemiumService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponseSchema)
async def get_user(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        raise AuthNotConnectedException()
    return UserResponseSchema.model_validate(user)


@router.get("/me/freemium", response_model=FreemiumStatusSchema)
async def get_freemium_status(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> FreemiumStatusSchema:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        raise AuthNotConnectedException()
    freemium_service = FreemiumService(user_repo=user_repo)
    return freemium_service.get_status(user)
