"""Authentication helpers for admin and application API keys."""

import os

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import App
from utils import hash_api_key

load_dotenv()

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")


def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    """Reject requests that do not present a valid admin secret."""
    if not ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_SECRET_KEY is not configured",
        )
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )


def get_current_app(
    x_app_key: str = Header(..., alias="X-App-Key"),
    db: Session = Depends(get_db),
) -> App:
    """
    Resolve and return the registered application for a given X-App-Key.

    The raw key is hashed and matched against app_key_hash. Inactive apps are rejected.
    """
    key_hash = hash_api_key(x_app_key)
    app = db.query(App).filter(App.app_key_hash == key_hash).first()

    if app is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid application key",
        )

    if not app.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application is inactive",
        )

    return app
