"""All API routes.

Everything below /api requires a valid token except the auth endpoints that
declare no dependency on it (status, register, login, logout).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth,
    cash,
    customers,
    health,
    home,
    items,
    reminders,
    reports,
    transactions,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)

# Credit Book
api_router.include_router(customers.router)
api_router.include_router(transactions.router)
api_router.include_router(reminders.router)
api_router.include_router(reports.router)

# Shared: products are Credit Book quick items AND ThathaCash stock
api_router.include_router(items.router)

# ThathaCash
api_router.include_router(cash.router)
api_router.include_router(home.router)
