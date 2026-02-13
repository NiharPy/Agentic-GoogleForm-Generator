from typing import TypedDict, Optional, Dict, Any, List

class ExecutorState(TypedDict, total=False):
    # Input from A2A message
    task_id: str
    conversation_id: str
    form_snapshot: Dict[str, Any]
    
    # Processing fields
    google_form_request: Optional[Dict[str, Any]]
    form_id: Optional[str]
    form_url: Optional[str]
    
    # Credentials
    access_token: Optional[str]
    refresh_token: Optional[str]
    
    # Status tracking
    status: str  # "pending", "processing", "completed", "failed"
    error: Optional[str]
    details: Optional[str]
    
    # Response to planner
    response_payload: Optional[Dict[str, Any]]