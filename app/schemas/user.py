from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    google_id: str
    email: str
    name: str
    picture: str | None = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str

    class Config:
        from_attributes = True
