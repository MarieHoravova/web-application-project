from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.PaymentService import PaymentService
from services.PaymentMethodService import PaymentMethodService
from services.BookingService import BookingService
from dependencies import payment_service, payment_method_service, booking_service
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
    # přihlašování – pokud není cookie/token, přesměrujeme na login
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]

    try:
        payments: List[Dict[str, Any]] = pay_svc.list_all_payments(
            current_user_role=role_id
        )
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


@router.get("/booking/{booking_id}", name="payments_by_booking")
async def payments_by_booking(
    booking_id: int,
    request: Request,
    pay_svc: PaymentService = Depends(payment_service),
    method_svc: PaymentMethodService = Depends(payment_method_service),
    booking_svc: BookingService = Depends(booking_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    booking = booking_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    try:
        payments: List[Dict[str, Any]] = pay_svc.list_payments_by_booking(
            booking_id=booking_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # např. "Booking neexistuje" – kdyby nastala závodní situace
        raise HTTPException(status_code=404, detail=str(e))

    methods = method_svc.list_methods()
    method_map = {m["id"]: m["description"] for m in methods}

    role_id = current_user["role_id"]

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "payments/payments_by_booking.html",
        {
            "request": request,
            "title": f"Platby pro booking {booking['code']}",
            "booking": booking,
            "payments": payments,
            "methods": methods,
            "method_map": method_map,
            "current_user": current_user,
            "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
            "is_admin": role_id == ROLE_ADMIN,
            "is_customer": role_id == ROLE_CUSTOMER,
        },
    )


@router.post("/booking/{booking_id}", name="payments_create_for_booking")
async def payments_create_for_booking(
    booking_id: int,
    request: Request,
    amount: float = Form(...),
    method_id: int = Form(...),
    pay_svc: PaymentService = Depends(payment_service),
    booking_svc: BookingService = Depends(booking_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    # kontrola existence bookingu
    booking = booking_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    try:
        pay_svc.create_payment(
            booking_id=booking_id,
            amount=amount,
            method_id=method_id,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("payments_by_booking", booking_id=booking_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/booking/{booking_id}/delete/{payment_id}", name="payment_delete")
async def payment_delete(
    booking_id: int,
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
        url=request.url_for("payments_by_booking", booking_id=booking_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
