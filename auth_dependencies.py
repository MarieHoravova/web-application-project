from typing import Any, Dict, Optional

from fastapi import Depends, Cookie
from fastapi.responses import RedirectResponse
from fastapi import HTTPException, status

from core.security import decode_access_token

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

ACCESS_COOKIE = "access_token"  # stejné jméno jako v set_cookie v AuthPage


def get_current_user(
    access_token: Optional[str] = Cookie(default=None, alias=ACCESS_COOKIE),
) -> Dict[str, Any] | RedirectResponse:
    """
    Vrátí dict s informacemi o uživateli z JWT,
    nebo RedirectResponse na /auth/login, pokud není/neplatný.
    """
    if not access_token:
        # Nepřihlášený → přesměrujeme na login
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        payload = decode_access_token(access_token)
    except ValueError:
        # Token expiroval / neplatný → taky na login
        return RedirectResponse(url="/auth/login", status_code=303)

    # payload: {"sub": "...", "roles": ["3"], "exp": ...}
    user_id = int(payload["sub"])
    roles = payload.get("roles", [])
    role_id = int(roles[0]) if roles else None  # z ["3"] uděláme 3

    return {
        "id": user_id,
        "role_id": role_id,
        "roles": roles,
    }


def require_roles(*allowed_roles: int):
    """
    Dependency, která:
    - nejdřív získá current_user z get_current_user
    - pokud není přihlášený → login redirect (řeší get_current_user)
    - pokud je, ale role_id není v allowed_roles → 403
    - jinak vrátí user dict
    """
    def dependency(user = Depends(get_current_user)):
        # Pokud get_current_user vrátil RedirectResponse,
        # FastAPI ho rovnou pošle klientovi a sem se to „logicky“ ani nedostane.
        if isinstance(user, RedirectResponse):
            return user

        if user["role_id"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nemáte oprávnění",
            )

        return user

    return dependency
