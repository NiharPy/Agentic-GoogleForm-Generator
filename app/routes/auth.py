from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.core.settings import get_settings
from app.core.security import create_access_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

settings = get_settings()

import httpx
from datetime import datetime, timedelta

@router.post("/google")
async def google_oauth(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Expects:
    {
        "code": "authorization_code_from_google"
    }
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code")

    token_data = response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    id_token_str = token_data["id_token"]
    expires_in = token_data["expires_in"]

    # Verify ID token
    idinfo = id_token.verify_oauth2_token(
        id_token_str,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID
    )

    google_id = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    # Check if user exists
    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()

    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            google_access_token=access_token,
            google_refresh_token=refresh_token,
            token_expiry=expiry_time,
        )
        db.add(user)
    else:
        user.google_access_token = access_token
        user.google_refresh_token = refresh_token or user.google_refresh_token
        user.token_expiry = expiry_time

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(
        {"user_id": str(user.id), "email": user.email}
    )

    return {
        "access_token": jwt_token,
        "token_type": "bearer"
    }

@router.get("/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    token_data = response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    id_token_str = token_data["id_token"]
    expires_in = token_data["expires_in"]

    # Verify ID token
    idinfo = id_token.verify_oauth2_token(
        id_token_str,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID
    )

    google_id = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()

    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            google_access_token=access_token,
            google_refresh_token=refresh_token,
            token_expiry=expiry_time,
        )
        db.add(user)
    else:
        user.google_access_token = access_token
        user.google_refresh_token = refresh_token or user.google_refresh_token
        user.token_expiry = expiry_time

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(
        {"user_id": str(user.id), "email": user.email}
    )

    return {
        "message": "Login successful",
        "jwt": jwt_token
    }

@router.get("/login")
async def google_login_redirect():
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/forms.body",
        "access_type": "offline",   # needed for refresh_token
        "prompt": "consent"         # forces refresh_token on first login
    }

    url = f"{google_auth_url}?{urlencode(params)}"
    return RedirectResponse(url)

