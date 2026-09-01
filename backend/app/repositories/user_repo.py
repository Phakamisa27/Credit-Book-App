"""User / account SQL. `password_hash` is only ever selected where it is needed
to verify a password — never on a path that returns a response body."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

PUBLIC_COLUMNS = """
  id, full_name, email, business_name, business_phone, profile_image,
  created_at, updated_at
"""

UPDATABLE_COLUMNS = {
    "fullName": "full_name",
    "businessName": "business_name",
    "businessPhone": "business_phone",
    "profileImage": "profile_image",
}


def find_by_email(db: Session, email: str) -> Any | None:
    sql = f"SELECT {PUBLIC_COLUMNS}, password_hash FROM users WHERE email = :email"
    return db.execute(text(sql), {"email": email}).mappings().first()


def exists_with_email(db: Session, email: str) -> bool:
    row = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).first()
    return row is not None


def find_by_id(db: Session, user_id: int) -> Any | None:
    sql = f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = :id"
    return db.execute(text(sql), {"id": user_id}).mappings().first()


def password_hash_for(db: Session, user_id: int) -> str | None:
    row = db.execute(
        text("SELECT password_hash FROM users WHERE id = :id"), {"id": user_id}
    ).first()
    return row[0] if row else None


def insert(db: Session, data: dict[str, Any]) -> Any:
    sql = f"""
        INSERT INTO users (full_name, email, password_hash, business_name, business_phone)
        VALUES (:full_name, :email, :password_hash, :business_name, :business_phone)
        RETURNING {PUBLIC_COLUMNS}
    """
    row = db.execute(text(sql), data).mappings().first()
    db.commit()
    return row


def update_columns(db: Session, user_id: int, patch: dict[str, Any]) -> Any | None:
    sets: list[str] = []
    params: dict[str, Any] = {"id": user_id}

    for key, column in UPDATABLE_COLUMNS.items():
        if key in patch:
            params[column] = patch[key]
            sets.append(f"{column} = :{column}")

    if not sets:
        return find_by_id(db, user_id)

    sets.append("updated_at = now()")
    sql = f"""
        UPDATE users SET {', '.join(sets)} WHERE id = :id
        RETURNING {PUBLIC_COLUMNS}
    """
    row = db.execute(text(sql), params).mappings().first()
    db.commit()
    return row


def set_password_hash(db: Session, user_id: int, password_hash: str) -> None:
    db.execute(
        text("UPDATE users SET password_hash = :hash, updated_at = now() WHERE id = :id"),
        {"hash": password_hash, "id": user_id},
    )
    db.commit()


def any_account_exists(db: Session) -> bool:
    return db.execute(text("SELECT 1 FROM users LIMIT 1")).first() is not None
