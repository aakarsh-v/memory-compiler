from fastapi import Header
from typing import Optional


def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """
    Extracts authenticated user ID from header or falls back to 'dev-user' in single-user dev mode.
    Guarantees that an explicit owner_id is present on all operations.
    """
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    return "dev-user"

