from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class RegisterRequest(RequestModel):
    fullName: Any = None
    email: Any = None
    password: Any = None
    confirmPassword: Any = None
    businessName: Any = None
    businessPhone: Any = None


class LoginRequest(RequestModel):
    email: Any = None
    password: Any = None


class UpdateMeRequest(RequestModel):
    fullName: Any = None
    businessName: Any = None
    businessPhone: Any = None
    profileImage: Any = None
    # Safe to draw settings.
    restockReserve: Any = None
    bufferPercent: Any = None


class ChangePasswordRequest(RequestModel):
    currentPassword: Any = None
    newPassword: Any = None
    confirmPassword: Any = None
