from typing import Dict
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

def profile_role_flags(current_user: dict) -> Dict[str, bool]:
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
        "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
    }
