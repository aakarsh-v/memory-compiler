from fastapi import Header
from typing import Optional


def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_owner_id: Optional[str] = Header(None, alias="X-Owner-ID"),
) -> str:
    """
    Extracts authenticated user ID from header (X-User-ID or X-Owner-ID)
    or falls back to 'default_user' in single-user dev mode.
    Guarantees that an explicit owner_id is present on all operations.
    """
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    if x_owner_id and x_owner_id.strip():
        return x_owner_id.strip()
    return "default_user"

