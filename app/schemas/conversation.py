from pydantic import BaseModel

class ConversationCreate(BaseModel):
    prompt: str  # the initial text or prompt for the conversation
