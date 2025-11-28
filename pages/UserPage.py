from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse

from services.UserService import UserService
from services.RoleService import RoleService

from dependencies import user_service, role_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

from helpers.profile_flags import profile_role_flags
router = APIRouter()

# logika pro editaci, show
def _get_user_detail_for_view(target_user_id: int, current_user, user_svc: UserService):
    user = user_svc.get_user_by_id(target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel neexistuje")

    role_id = current_user["role_id"]
    # True/false
    is_owner = target_user_id == current_user["id"]

    if role_id == ROLE_ADMIN:
        can_edit = True
    elif role_id in (ROLE_RECEPTIONIST, ROLE_CUSTOMER):
        can_edit = is_owner
    else:
        can_edit = False

    return user, is_owner, can_edit



@router.get("/", name="users_list")
async def users_list(
    request: Request,
    role_id: Optional[str] = Query(default=None),
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = profile_role_flags(current_user)
    current_role = current_user["role_id"]

    users: List[Dict[str, Any]]
    filter_role_id: Optional[int] = None
    roles: List[Dict[str, Any]] = []

    if current_role == ROLE_ADMIN:
        # role_id může být:
        # - None (parametr vůbec nepřišel)
        # - "" (uživatel vybral "-- všechny role --")
        # - "1", "2", ... (konkrétní role)
        if role_id not in (None, ""):
            try:
                role_id_int = int(role_id)
            except ValueError:
                # když je tam bordel, prostě ignoruj filtr
                users = user_svc.list_users(current_user_role=ROLE_ADMIN)
            else:
                try:
                    users = user_svc.list_users_by_role(role_id_int, current_user_role=ROLE_ADMIN)
                    filter_role_id = role_id_int
                except PermissionError as e:
                    raise HTTPException(status_code=403, detail=str(e))
        else:
            # žádný filtr → všechny role
            users = user_svc.list_users(current_user_role=ROLE_ADMIN)

        roles = role_svc.list_roles()

    elif current_role == ROLE_RECEPTIONIST:
        try:
            users = user_svc.list_users(current_user_role=ROLE_RECEPTIONIST)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    else:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit seznam uživatelů")

    return request.app.state.templates.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "title": "Seznam uživatelů",
            "users": users,
            "roles": roles,
            "filter_role_id": filter_role_id,
            "current_user": current_user,
            **flags,
        },
    )




@router.get("/{user_id}", name="user_detail")
async def user_detail(
    user_id: int,
    request: Request,
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = profile_role_flags(current_user)
    user, is_owner, can_edit = _get_user_detail_for_view(user_id, current_user, user_svc)

    role_id = current_user["role_id"]

    if role_id == ROLE_CUSTOMER and not is_owner:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit tohoto uživatele")

    roles = role_svc.list_roles() if flags["is_admin"] else []

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "users/user_detail.html",
        {
            "request": request,
            "title": f"Detail uživatele {user['email']}",
            "user": user,
            "current_user": current_user,
            "is_owner": is_owner,
            "can_edit": can_edit,
            "roles": roles,
            **flags,
        },
    )


@router.post("/{user_id}/role", name="user_change_role")
async def user_change_role(
    user_id: int,
    request: Request,
    role_id: int = Form(...),
    user_svc: UserService = Depends(user_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        user_svc.change_role(
            user_id=user_id,
            role_id=role_id,
            current_user_role=current_user["role_id"],
        )
    # Nemá oprávněnní měnit
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    # Chybná hodnota
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("user_detail", user_id=user_id),
        status_code=303,
    )



# = zobrazí formulář, načte uživatele z DB, zkontroluje práva a vrátí šablonu
# users/user_edit.html s předvyplněnými hodnotami.
@router.get("/{user_id}/edit", name="user_edit")
async def user_edit(
    user_id: int,
    request: Request,
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = profile_role_flags(current_user)
    #
    user, is_owner, can_edit = _get_user_detail_for_view(user_id, current_user, user_svc)

    if not can_edit:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat tento profil")

    roles: List[Dict[str, Any]] = role_svc.list_roles() if flags["is_admin"] else []

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "users/user_edit.html",
        {
            "request": request,
            "title": f"Upravit uživatele {user['email']}",
            "user": user,
            "current_user": current_user,
            "roles": roles,
            **flags,
        },
    )


# po submitu jde POST na user_update, ten uloží změny a redirectne na detail.
@router.post("/{user_id}", name="user_update")
async def user_update(
    user_id: int,
    request: Request,
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: Optional[str] = Form(None),
    user_svc: UserService = Depends(user_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        user_svc.update_user_profile(
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # tady je to buď "uživatel neexistuje" nebo jiná validační chyba
        msg = str(e)
        status_code = 404 if "neexistuje" in msg else 400
        raise HTTPException(status_code=status_code, detail=msg)

    return RedirectResponse(
        url=request.url_for("user_detail", user_id=user_id),
        status_code=303,
    )


# Mazání uživatele
@router.post("/{user_id}/delete", name="user_delete")
async def user_delete(
    user_id: int,
    request: Request,
    user_svc: UserService = Depends(user_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        user_svc.delete_user(
            target_user_id=user_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "neexistuje" in msg else 400
        raise HTTPException(status_code=status_code, detail=msg)

    if current_user["role_id"] == ROLE_ADMIN and current_user["id"] != user_id:
        return RedirectResponse(url=request.url_for("users_list"), status_code=303)

    return RedirectResponse(url=request.url_for("auth_logout"), status_code=303)
