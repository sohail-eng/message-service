"""Pydantic request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Admin / Apps ---


class AppRegisterRequest(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=255, examples=["CRM System"])


class AppRegisterResponse(BaseModel):
    app_name: str
    app_key: str


class AppInfo(BaseModel):
    id: int
    app_name: str
    created_at: datetime
    active: bool

    model_config = {"from_attributes": True}


# --- Messages ---


class MessageSendRequest(BaseModel):
    phone_number: str = Field(..., min_length=5, max_length=32, examples=["+923001234567"])
    message: str = Field(..., min_length=1, examples=["Hello customer"])


class MessageSendResponse(BaseModel):
    success: bool
    app_name: str
    message_id: int


class MessageOut(BaseModel):
    id: int
    app_name: str
    phone_number: str
    message: str
    created_at: datetime


class MessageDeleteResponse(BaseModel):
    deleted: bool


class MessageProcessResponse(BaseModel):
    id: int
    status: Literal["processed"]


# --- Health ---


class HealthResponse(BaseModel):
    status: str
