from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse

from services.UserService import UserService
from services.RoleService import RoleService
from dependencies import user_service, role_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


router = APIRouter()


@router.get("/", name="users_list")
async def users_list(
    request: Request,
    role_id: Optional[int] = None,
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    current_role = current_user["role_id"]

    users: List[Dict[str, Any]]
    filter_role_id: Optional[int] = None
    roles: List[Dict[str, Any]] = []

    if current_role == ROLE_ADMIN:
        if role_id is not None:
            try:
                users = user_svc.list_users_by_role(role_id, current_user_role=ROLE_ADMIN)
                filter_role_id = role_id
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
        else:
            users = user_svc.list_users(current_user_role=ROLE_ADMIN)

        roles = role_svc.list_roles()

    elif current_role == ROLE_RECEPTIONIST:
        try:
            users = user_svc.list_users(current_user_role=ROLE_RECEPTIONIST)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    else:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit seznam uživatelů")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "title": "Seznam uživatelů",
            "users": users,
            "roles": roles,
            "filter_role_id": filter_role_id,
            "current_user": current_user,
            "is_admin": current_role == ROLE_ADMIN,
            "is_receptionist": current_role == ROLE_RECEPTIONIST,
        },
    )




def _get_user_detail_for_view(target_user_id: int, current_user, user_svc: UserService):
    user = user_svc.get_user_by_id(target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel neexistuje")

    role_id = current_user["role_id"]
    is_owner = target_user_id == current_user["id"]

    if role_id == ROLE_ADMIN:
        can_edit = True
    elif role_id in (ROLE_RECEPTIONIST, ROLE_CUSTOMER):
        can_edit = is_owner
    else:
        can_edit = False

    return user, is_owner, can_edit


@router.get("/me", name="user_profile")
async def user_profile(
    request: Request,
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    user, is_owner, can_edit = _get_user_detail_for_view(current_user["id"], current_user, user_svc)

    roles = role_svc.list_roles() if current_user["role_id"] == ROLE_ADMIN else []

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "users/user_detail.html",
        {
            "request": request,
            "title": "Můj profil",
            "user": user,
            "current_user": current_user,
            "is_owner": is_owner,
            "can_edit": can_edit,
            "roles": roles,
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

    user, is_owner, can_edit = _get_user_detail_for_view(user_id, current_user, user_svc)

    role_id = current_user["role_id"]

    if role_id == ROLE_CUSTOMER and not is_owner:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit tohoto uživatele")

    roles = role_svc.list_roles() if role_id == ROLE_ADMIN else []

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
        },
    )


@router.post("/{user_id}", name="user_update")
async def user_update(
    user_id: int,
    request: Request,
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: Optional[str] = Form(None),
    user_svc: UserService = Depends(user_service),
    role_svc: RoleService = Depends(role_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    current_role = current_user["role_id"]
    current_user_id = current_user["id"]

    user = user_svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel neexistuje")

    if current_role != ROLE_ADMIN and current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat tento profil")

    try:
        user_svc.update_user_profile(
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("user_detail", user_id=user_id),
        status_code=303,
    )


@router.post("/{user_id}/role", name="user_change_role")
async def user_change_role(
    user_id: int,
    request: Request,
    role_id: int = Form(...),
    user_svc: UserService = Depends(user_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    current_role = current_user["role_id"]

    if current_role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Pouze admin může měnit role")

    try:
        user_svc.change_role(user_id=user_id, role_id=role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("user_detail", user_id=user_id),
        status_code=303,
    )

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

    current_role = current_user["role_id"]
    current_user_id = current_user["id"]

    user = user_svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel neexistuje")

    # práva: admin může editovat kohokoliv, ostatní jen sami sebe
    if current_role != ROLE_ADMIN and current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat tento profil")

    roles: List[Dict[str, Any]] = role_svc.list_roles() if current_role == ROLE_ADMIN else []

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "users/user_edit.html",
        {
            "request": request,
            "title": f"Upravit uživatele {user['email']}",
            "user": user,
            "current_user": current_user,
            "is_admin": current_role == ROLE_ADMIN,
            "roles": roles,
        },
    )
