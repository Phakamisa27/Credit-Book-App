"""SQLAlchemy models — one file per table, matching backend/src/db/schema.sql."""

from app.models.customer import Customer
from app.models.item import Item
from app.models.reminder import STATUSES, Reminder
from app.models.transaction import CREDIT, PAYMENT, TYPES, Transaction
from app.models.transaction_item import TransactionItem
from app.models.user import User

__all__ = [
    "CREDIT",
    "PAYMENT",
    "STATUSES",
    "TYPES",
    "Customer",
    "Item",
    "Reminder",
    "Transaction",
    "TransactionItem",
    "User",
]
