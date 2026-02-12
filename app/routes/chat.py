from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    session_id: str
    message: str

@router.post("/")
async def chat_endpoint(request: ChatRequest):
    return {
        "session_id": request.session_id,
        "message": request.message,
        "status": "received"
    }
