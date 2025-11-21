from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.PaymentService import PaymentService
from services.PaymentMethodService import PaymentMethodService
from services.ReservationService import ReservationService
from dependencies import payment_service, payment_method_service, reservation_service
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER
from auth_dependencies import get_current_user

router = APIRouter()


@router.get("/", name="payments_list")
async def payments_list(
    request: Request,
    pay_svc: PaymentService = Depends(payment_service),
    method_svc: PaymentMethodService = Depends(payment_method_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]

    try:
        payments: List[Dict[str, Any]] = pay_svc.list_all_payments(current_user_role=role_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    methods = method_svc.list_methods()
    method_map = {m["id"]: m["description"] for m in methods}

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "payments/payments_list.html",
        {
            "request": request,
            "title": "Seznam všech plateb",
            "payments": payments,
            "method_map": method_map,
            "current_user": current_user,
            "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
            "is_admin": role_id == ROLE_ADMIN,
            "is_customer": role_id == ROLE_CUSTOMER,
        },
    )


@router.get("/reservation/{reservation_id}", name="payments_by_reservation")
async def payments_by_reservation(
    reservation_id: int,
    request: Request,
    pay_svc: PaymentService = Depends(payment_service),
    method_svc: PaymentMethodService = Depends(payment_method_service),
    reservation_svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    reservation = reservation_svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    try:
        payments: List[Dict[str, Any]] = pay_svc.list_payments_by_reservation(
            reservation_id=reservation_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # např. "Rezervace neexistuje"
        raise HTTPException(status_code=404, detail=str(e))

    methods = method_svc.list_methods()
    method_map = {m["id"]: m["description"] for m in methods}

    role_id = current_user["role_id"]

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "payments/payments_by_reservation.html",
        {
            "request": request,
            "title": f"Platby pro rezervaci {reservation['code']}",
            "reservation": reservation,
            "payments": payments,
            "methods": methods,
            "method_map": method_map,
            "current_user": current_user,
            "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
            "is_admin": role_id == ROLE_ADMIN,
            "is_customer": role_id == ROLE_CUSTOMER,
        },
    )


@router.post("/reservation/{reservation_id}", name="payments_create_for_reservation")
async def payments_create_for_reservation(
    reservation_id: int,
    request: Request,
    amount: float = Form(...),
    method_id: int = Form(...),
    pay_svc: PaymentService = Depends(payment_service),
    reservation_svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    reservation = reservation_svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    try:
        pay_svc.create_payment(
            reservation_id=reservation_id,
            amount=amount,
            method_id=method_id,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("payments_by_reservation", reservation_id=reservation_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/reservation/{reservation_id}/delete/{payment_id}", name="payment_delete")
async def payment_delete(
    reservation_id: int,
    payment_id: int,
    request: Request,
    pay_svc: PaymentService = Depends(payment_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        pay_svc.delete_payment(
            payment_id=payment_id,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("payments_by_reservation", reservation_id=reservation_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
