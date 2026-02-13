from typing import TypedDict, Optional, Dict, Any, List

class PlannerState(TypedDict, total=False):
    # Input fields
    user_prompt: str
    documents: Optional[str]
    form_snapshot: Optional[Dict[str, Any]]
    conversation_id: str
    
    # Processing fields
    llm_input: str
    llm_output: Optional[Dict[str, Any]]
    
    # RAG fields
    query_embedding: Optional[List[float]]
    similar_forms: Optional[List[Dict[str, Any]]]
    rag_context: Optional[str]
    
    # Control flow fields
    follow_up_required: bool
    error: Optional[str]
    details: Optional[str]
    
    # Optional fields for extended functionality
    uploaded_files: Optional[List[str]]
    existing_snapshot: Optional[Dict[str, Any]]
    conversation_history: Optional[List[Dict[str, Any]]]