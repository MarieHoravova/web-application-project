from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from starlette import status

from services.AuthService import AuthService
from dependencies import auth_service
from models.Auth import RegisterRequest
from pydantic import ValidationError
router = APIRouter()


@router.get("/login", name="auth_login")
async def auth_login_get(request: Request):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "auth/auth_login.html",
        {
            "request": request,
            "title": "Přihlášení",
            "error": None,
            "token": None,
        },
    )


@router.post("/login", name="auth_login_post")
async def auth_login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    svc: AuthService = Depends(auth_service),
):
    tpl = request.app.state.templates
    try:
        token = svc.login(email, password)
    except ValueError as e:
        # špatné přihlášení → vrátíme formulář s chybou
        return tpl.TemplateResponse(
            "auth/auth_login.html",
            {
                "request": request,
                "title": "Přihlášení",
                "error": str(e),
                "token": None,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # ÚSPĚŠNÝ LOGIN:
    response = RedirectResponse(
        url=request.url_for("user_profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response

@router.get("/logout", name="auth_logout")
async def auth_logout(request: Request):
    response = RedirectResponse(
        url=request.url_for("auth_login"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie("access_token")
    return response


@router.get("/register", name="auth_register")
async def auth_register_get(request: Request):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "auth/auth_register.html",
        {
            "request": request,
            "title": "Registrace",
            "error": None,
        },
    )



@router.post("/register", name="auth_register_post")
async def auth_register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: str = Form(...),
    svc: AuthService = Depends(auth_service),
):
    from models.Auth import RegisterRequest

    tpl = request.app.state.templates

    try:
        data = RegisterRequest(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        svc.register(data)

    except ValidationError as e:
        errors = e.errors()
        messages = []
        for err in errors:
            msg = err["msg"]  # např. "Value error, Heslo musí mít alespoň 6 znaků"
            prefix = "Value error, "
            if msg.startswith(prefix):
                msg = msg[len(prefix):]  # => "Heslo musí mít alespoň 6 znaků"
            messages.append(msg)

        friendly_error = " ".join(messages)

        return tpl.TemplateResponse(
            "auth/auth_register.html",
            {
                "request": request,
                "title": "Registrace",
                "error": friendly_error,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    except ValueError as e:
        return tpl.TemplateResponse(
            "auth/auth_register.html",
            {
                "request": request,
                "title": "Registrace",
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(
        url=request.url_for("auth_login"),
        status_code=status.HTTP_303_SEE_OTHER,
    )