from fastapi import Depends, HTTPException, status

from app.core.security import check_permission, get_current_user


def require_permission(required_action: str):
    async def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role", "Personel")
        if not check_permission(role, required_action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_action}",
            )
        return current_user

    return _dependency

