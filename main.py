"""WhatsApp Message Gateway — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_app, verify_admin_key
from database import Base, engine, get_db
from models import App, Message
from schemas import (
    AppInfo,
    AppRegisterRequest,
    AppRegisterResponse,
    HealthResponse,
    MessageDeleteResponse,
    MessageOut,
    MessageProcessResponse,
    MessageSendRequest,
    MessageSendResponse,
)
from utils import generate_api_key, hash_api_key


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="WhatsApp Message Gateway",
    description="Lightweight gateway for registering apps and queuing WhatsApp messages.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin — application management
# ---------------------------------------------------------------------------


@app.post(
    "/admin/apps/register",
    response_model=AppRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
)
def register_app(payload: AppRegisterRequest, db: Session = Depends(get_db)):
    """Register a new application and return its API key once."""
    existing = db.query(App).filter(App.app_name == payload.app_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this name already exists",
        )

    raw_key = generate_api_key()
    app_record = App(
        app_name=payload.app_name,
        app_key_hash=hash_api_key(raw_key),
        active=True,
    )
    db.add(app_record)
    db.commit()
    db.refresh(app_record)

    return AppRegisterResponse(app_name=app_record.app_name, app_key=raw_key)


@app.get(
    "/admin/apps",
    response_model=list[AppInfo],
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
)
def list_apps(db: Session = Depends(get_db)):
    """List registered applications (API keys are never exposed)."""
    return db.query(App).order_by(App.id).all()


@app.delete(
    "/admin/apps/{app_id}",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
)
def delete_app(app_id: int, db: Session = Depends(get_db)):
    """Permanently delete a registered application and its messages."""
    app_record = db.query(App).filter(App.id == app_id).first()
    if app_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    app_name = app_record.app_name
    db.delete(app_record)
    db.commit()

    return {"deleted": True, "id": app_id, "app_name": app_name}


# ---------------------------------------------------------------------------
# Messages — application-scoped operations
# ---------------------------------------------------------------------------


@app.post(
    "/messages/send",
    response_model=MessageSendResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Messages"],
)
def send_message(
    payload: MessageSendRequest,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """Queue a WhatsApp message for the authenticated application."""
    msg = Message(
        app_id=current_app.id,
        phone_number=payload.phone_number,
        message=payload.message,
        status="pending",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return MessageSendResponse(
        success=True,
        app_name=current_app.app_name,
        message_id=msg.id,
    )


@app.get(
    "/messages",
    response_model=list[MessageOut],
    tags=["Messages"],
    dependencies=[Depends(verify_admin_key)],
)
def get_pending_messages(db: Session = Depends(get_db)):
    """Return all pending messages (admin). Used by the WhatsApp worker/bot."""
    messages = (
        db.query(Message)
        .join(App)
        .filter(Message.status == "pending")
        .order_by(Message.created_at.asc())
        .all()
    )

    return [
        MessageOut(
            id=m.id,
            app_name=m.app.app_name,
            phone_number=m.phone_number,
            message=m.message,
            created_at=m.created_at,
        )
        for m in messages
    ]


@app.delete(
    "/messages/{message_id}",
    response_model=MessageDeleteResponse,
    tags=["Messages"],
)
def delete_message(
    message_id: int,
    current_app: App = Depends(get_current_app),
    db: Session = Depends(get_db),
):
    """Delete a message that belongs to the authenticated application."""
    msg = (
        db.query(Message)
        .filter(Message.id == message_id, Message.app_id == current_app.id)
        .first()
    )
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    db.delete(msg)
    db.commit()

    return MessageDeleteResponse(deleted=True)


@app.post(
    "/messages/{message_id}/process",
    response_model=MessageProcessResponse,
    tags=["Messages"],
    dependencies=[Depends(verify_admin_key)],
)
def process_message(message_id: int, db: Session = Depends(get_db)):
    """Mark a message as processed (admin). Used by the WhatsApp worker/bot."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if msg.status == "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Message is already processed",
        )

    msg.status = "processed"
    db.commit()
    db.refresh(msg)

    return MessageProcessResponse(id=msg.id, status="processed")
