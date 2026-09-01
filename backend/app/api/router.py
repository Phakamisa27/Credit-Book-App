"""All API routes.

Everything below /api requires a valid token except the auth endpoints that
declare no dependency on it (status, register, login, logout).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, customers, health, items, reminders, reports, transactions

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(transactions.router)
api_router.include_router(reminders.router)
api_router.include_router(reports.router)
api_router.include_router(items.router)
