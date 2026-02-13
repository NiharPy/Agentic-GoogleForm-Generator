from app.agents.executor.state import ExecutorState
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


async def convert_to_google_forms_node(state: ExecutorState) -> ExecutorState:
    """
    Node 2: Convert form snapshot to Google Forms API request format
    
    Transforms our internal schema into Google Forms API batch update requests
    
    Returns:
        Updated state with google_form_request
    """
    
    form_snapshot = state.get("form_snapshot")
    
    if not form_snapshot:
        logger.error("No form_snapshot in state")
        return {
            **state,
            "status": "failed",
            "error": "missing_form_snapshot"
        }
    
    try:
        # Extract form metadata
        title = form_snapshot.get("title", "Untitled Form")
        description = form_snapshot.get("description", "")
        fields = form_snapshot.get("fields", [])
        
        logger.info(f"🔄 Converting form '{title}' with {len(fields)} fields")
        
        # Build batch update requests
        requests = []
        
        # 1️⃣ Update form info (title and description)
        requests.append({
            "updateFormInfo": {
                "info": {
                    "title": title,
                    "documentTitle": title
                },
                "updateMask": "title,documentTitle"
            }
        })
        
        if description:
            requests.append({
                "updateFormInfo": {
                    "info": {
                        "description": description
                    },
                    "updateMask": "description"
                }
            })
        
        # 2️⃣ Create questions for each field
        for index, field in enumerate(fields):
            question_request = _convert_field_to_question(field, index)
            if question_request:
                requests.append(question_request)
        
        # 3️⃣ Add settings if present
        settings = form_snapshot.get("settings")
        if settings:
            settings_request = _convert_settings(settings)
            if settings_request:
                requests.append(settings_request)
        
        logger.info(f"✅ Generated {len(requests)} Google Forms API requests")
        
        return {
            **state,
            "google_form_request": {
                "title": title,
                "requests": requests
            },
            "status": "processing"
        }
    
    except Exception as e:
        logger.error(f"Failed to convert to Google Forms format: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error": "conversion_error",
            "details": str(e)
        }


def _convert_field_to_question(field: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Convert a single field to a Google Forms question request
    
    Field types mapping:
    - text -> TEXT
    - paragraph -> PARAGRAPH
    - email -> TEXT with email validation
    - phone -> TEXT with custom validation
    - number -> TEXT with number validation
    - dropdown -> DROPDOWN
    - checkbox -> CHECKBOX
    - radio -> MULTIPLE_CHOICE
    - date -> DATE
    - time -> TIME
    - file -> FILE_UPLOAD
    - rating -> SCALE (1-5 or 1-10)
    """
    
    field_type = field.get("type", "text")
    label = field.get("label", "Question")
    required = field.get("required", False)
    
    # Base question structure
    question = {
        "createItem": {
            "item": {
                "title": label,
                "questionItem": {
                    "question": {
                        "required": required
                    }
                }
            },
            "location": {
                "index": index
            }
        }
    }
    
    # Map our field types to Google Forms question types
    if field_type == "text":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    elif field_type == "paragraph":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": True
        }
    
    elif field_type == "email":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
        # Add email validation
        question["createItem"]["item"]["questionItem"]["question"]["textValidation"] = {
            "type": "IS_EMAIL"
        }
    
    elif field_type == "phone":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    elif field_type == "number":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
        # Add number validation
        validation = field.get("validation", {})
        if validation:
            question["createItem"]["item"]["questionItem"]["question"]["textValidation"] = {
                "type": "IS_NUMBER"
            }
    
    elif field_type == "dropdown":
        options = field.get("options", [])
        question["createItem"]["item"]["questionItem"]["question"]["choiceQuestion"] = {
            "type": "DROP_DOWN",
            "options": [{"value": opt} for opt in options]
        }
    
    elif field_type == "checkbox":
        options = field.get("options", [])
        question["createItem"]["item"]["questionItem"]["question"]["choiceQuestion"] = {
            "type": "CHECKBOX",
            "options": [{"value": opt} for opt in options]
        }
    
    elif field_type == "radio":
        options = field.get("options", [])
        question["createItem"]["item"]["questionItem"]["question"]["choiceQuestion"] = {
            "type": "RADIO",
            "options": [{"value": opt} for opt in options]
        }
    
    elif field_type == "date":
        question["createItem"]["item"]["questionItem"]["question"]["dateQuestion"] = {
            "includeTime": False,
            "includeYear": True
        }
    
    elif field_type == "time":
        question["createItem"]["item"]["questionItem"]["question"]["timeQuestion"] = {
            "duration": False
        }
    
    elif field_type == "file":
        question["createItem"]["item"]["questionItem"]["question"]["fileUploadQuestion"] = {
            "folderId": "",  # Will use default folder
            "maxFiles": 1,
            "maxFileSize": 10485760  # 10MB
        }
    
    elif field_type == "rating":
        validation = field.get("validation", {})
        min_val = validation.get("min", 1)
        max_val = validation.get("max", 5)
        
        question["createItem"]["item"]["questionItem"]["question"]["scaleQuestion"] = {
            "low": min_val,
            "high": max_val,
            "lowLabel": str(min_val),
            "highLabel": str(max_val)
        }
    
    else:
        # Default to text question
        logger.warning(f"Unknown field type '{field_type}', defaulting to text")
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    return question


def _convert_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert form settings to Google Forms settings request
    """
    
    settings_update = {
        "updateSettings": {
            "settings": {},
            "updateMask": []
        }
    }
    
    # Quiz mode
    if "is_quiz" in settings:
        settings_update["updateSettings"]["settings"]["quizSettings"] = {
            "isQuiz": settings["is_quiz"]
        }
        settings_update["updateSettings"]["updateMask"].append("quizSettings")
    
    # Collect email
    if settings.get("collect_email"):
        settings_update["updateSettings"]["settings"]["requireLoginSettings"] = {
            "requireLogin": True
        }
        settings_update["updateSettings"]["updateMask"].append("requireLoginSettings")
    
    # Allow multiple responses
    if "allow_multiple_responses" in settings:
        # This is controlled at the form level, not in settings API
        pass
    
    # Confirmation message
    if "confirmation_message" in settings:
        settings_update["updateSettings"]["settings"]["confirmationMessage"] = {
            "text": settings["confirmation_message"]
        }
        settings_update["updateSettings"]["updateMask"].append("confirmationMessage")
    
    # Join update mask into comma-separated string
    if settings_update["updateSettings"]["updateMask"]:
        settings_update["updateSettings"]["updateMask"] = ",".join(
            settings_update["updateSettings"]["updateMask"]
        )
        return settings_update
    
    return None
