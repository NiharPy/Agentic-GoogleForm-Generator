# app/core/google_forms.py
"""
FIXED: Google Forms creation with proper field type handling

This fixes the issue where all fields were showing as "Short-answer text"
ALSO handles Google Forms API limitations (file upload not supported via API)
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timezone
import logging
from app.core.settings import settings

logger = logging.getLogger(__name__)


SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive.file",
]


async def refresh_if_expired(user, db):
    """Refresh Google access token if expired."""
    
    if not user.token_expiry:
        return user.google_access_token

    if user.token_expiry > datetime.now(timezone.utc):
        return user.google_access_token

    logger.info("🔄 Refreshing expired Google access token")

    # Get credentials from environment
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Google OAuth credentials. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    creds.refresh(Request())

    user.google_access_token = creds.token
    user.token_expiry = creds.expiry

    await db.commit()

    return creds.token


def convert_field_to_question(field, index):
    """
    Convert a field to Google Forms question format
    
    FIXED: Now properly handles all field types!
    UPDATED: Skips file upload fields (not supported by API)
    """
    
    field_type = field.get("type", "text")
    label = field.get("label", "Question")
    required = field.get("required", False)
    
    # ⚠️ GOOGLE FORMS API LIMITATION: File upload not supported
    if field_type == "file":
        logger.warning(f"⚠️ Skipping file upload field '{label}' - not supported by Google Forms API")
        logger.info("💡 File upload questions must be added manually in Google Forms UI")
        return None  # Skip this field
    
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
    
    # Map field types to Google Forms question types
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
    
    elif field_type == "phone":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    elif field_type == "number":
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    elif field_type == "dropdown":
        # FIXED: Properly create dropdown
        options = field.get("options", [])
        question["createItem"]["item"]["questionItem"]["question"]["choiceQuestion"] = {
            "type": "DROP_DOWN",
            "options": [{"value": opt} for opt in options]
        }
    
    elif field_type == "checkbox":
        # FIXED: Properly create checkbox
        options = field.get("options", [])
        question["createItem"]["item"]["questionItem"]["question"]["choiceQuestion"] = {
            "type": "CHECKBOX",
            "options": [{"value": opt} for opt in options]
        }
    
    elif field_type == "radio":
        # FIXED: Properly create radio (multiple choice)
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
    
    else:
        # Default to text
        logger.warning(f"Unknown field type '{field_type}', defaulting to text")
        question["createItem"]["item"]["questionItem"]["question"]["textQuestion"] = {
            "paragraph": False
        }
    
    return question


async def create_google_form(user, form_snapshot, db):
    """
    Create a Google Form using the Forms API
    
    FIXED: Now properly converts all field types
    UPDATED: Handles file upload limitation gracefully
    """

    access_token = await refresh_if_expired(user, db)

    # Get credentials from environment
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Google OAuth credentials. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    creds = Credentials(
        token=access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    service = build("forms", "v1", credentials=creds)

    # 1️⃣ Create empty form
    form = service.forms().create(
        body={
            "info": {
                "title": form_snapshot.get("title", "Untitled Form"),
                "documentTitle": form_snapshot.get("title", "Untitled Form"),
            }
        }
    ).execute()

    form_id = form["formId"]
    logger.info(f"✅ Created form with ID: {form_id}")

    # 2️⃣ Add description if present
    description = form_snapshot.get("description", "")
    if description:
        service.forms().batchUpdate(
            formId=form_id,
            body={
                "requests": [{
                    "updateFormInfo": {
                        "info": {
                            "description": description
                        },
                        "updateMask": "description"
                    }
                }]
            }
        ).execute()

    # 3️⃣ Add questions with PROPER field types (skip unsupported ones)
    requests = []
    skipped_fields = []
    
    for index, field in enumerate(form_snapshot.get("fields", [])):
        question = convert_field_to_question(field, index - len(skipped_fields))
        
        if question is None:
            # Field was skipped (e.g., file upload)
            skipped_fields.append(field.get("label"))
            continue
            
        requests.append(question)

    if requests:
        logger.info(f"📤 Adding {len(requests)} questions with proper field types")
        
        service.forms().batchUpdate(
            formId=form_id,
            body={"requests": requests}
        ).execute()
        
        logger.info("✅ Questions added successfully")
    
    # Log skipped fields
    if skipped_fields:
        logger.warning(f"⚠️ Skipped {len(skipped_fields)} unsupported fields: {', '.join(skipped_fields)}")
        logger.info("💡 These fields must be added manually in Google Forms:")
        for field_name in skipped_fields:
            logger.info(f"   - {field_name}")

    # 4️⃣ Apply settings if present
    form_settings = form_snapshot.get("settings", {})
    if form_settings:
        settings_requests = []
        
        # Collect email setting
        if form_settings.get("collect_email"):
            settings_requests.append({
                "updateSettings": {
                    "settings": {
                        "quizSettings": {
                            "isQuiz": False
                        }
                    },
                    "updateMask": "quizSettings"
                }
            })
        
        if settings_requests:
            service.forms().batchUpdate(
                formId=form_id,
                body={"requests": settings_requests}
            ).execute()

    # Get final form with responder URI
    final_form = service.forms().get(formId=form_id).execute()
    form_url = final_form.get("responderUri", f"https://docs.google.com/forms/d/{form_id}/edit")

    if skipped_fields:
        logger.warning(f"⚠️ Form created with {len(requests)} fields. {len(skipped_fields)} fields skipped (file uploads must be added manually)")
    
    logger.info(f"✅ Form created successfully: {form_url}")

    return form_id, form_url


# Add this to app/core/google_forms.py

async def update_google_form(user, form_id: str, form_snapshot: dict, db):
    """
    Update an existing Google Form
    
    Strategy:
    1. Refresh token if needed
    2. Get current form
    3. Delete all existing questions
    4. Add new questions from updated form_snapshot
    5. Update form title/description if changed
    
    Args:
        user: User object with Google credentials
        form_id: Existing Google Form ID
        form_snapshot: Updated form schema
        db: Database session
        
    Returns:
        tuple: (form_id, form_url)
    """
    
    access_token = await refresh_if_expired(user, db)

    # Get credentials from environment
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Google OAuth credentials. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    creds = Credentials(
        token=access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    service = build("forms", "v1", credentials=creds)

    logger.info(f"🔄 Updating form {form_id}")

    # 1️⃣ Get current form to find existing items
    try:
        current_form = service.forms().get(formId=form_id).execute()
    except Exception as e:
        logger.error(f"Failed to get form {form_id}: {e}")
        raise

    # 2️⃣ Delete all existing questions
    existing_items = current_form.get("items", [])
    
    if existing_items:
        delete_requests = []
        for item in existing_items:
            # Delete from position 0 repeatedly (as items shift down)
            delete_requests.append({
                "deleteItem": {
                    "location": {
                        "index": 0
                    }
                }
            })
        
        logger.info(f"🗑️  Deleting {len(delete_requests)} existing questions")
        
        try:
            service.forms().batchUpdate(
                formId=form_id,
                body={"requests": delete_requests}
            ).execute()
        except Exception as e:
            logger.error(f"Failed to delete existing questions: {e}")
            # Continue anyway - we'll add new questions

    # 3️⃣ Update form info (title and description) if changed
    title = form_snapshot.get("title", "Untitled Form")
    description = form_snapshot.get("description", "")
    
    info_requests = []
    
    if title != current_form.get("info", {}).get("title"):
        info_requests.append({
            "updateFormInfo": {
                "info": {
                    "title": title,
                    "documentTitle": title
                },
                "updateMask": "title,documentTitle"
            }
        })
    
    if description and description != current_form.get("info", {}).get("description"):
        info_requests.append({
            "updateFormInfo": {
                "info": {
                    "description": description
                },
                "updateMask": "description"
            }
        })
    
    if info_requests:
        logger.info("📝 Updating form title/description")
        service.forms().batchUpdate(
            formId=form_id,
            body={"requests": info_requests}
        ).execute()

    # 4️⃣ Add new questions (skip unsupported ones like file upload)
    requests = []
    skipped_fields = []
    
    for index, field in enumerate(form_snapshot.get("fields", [])):
        question = convert_field_to_question(field, index - len(skipped_fields))
        
        if question is None:
            # Field was skipped (e.g., file upload)
            skipped_fields.append(field.get("label"))
            continue
            
        requests.append(question)

    if requests:
        logger.info(f"📤 Adding {len(requests)} new questions")
        
        service.forms().batchUpdate(
            formId=form_id,
            body={"requests": requests}
        ).execute()
        
        logger.info("✅ Questions added successfully")
    
    # Log skipped fields
    if skipped_fields:
        logger.warning(f"⚠️ Skipped {len(skipped_fields)} unsupported fields: {', '.join(skipped_fields)}")

    # 5️⃣ Get final form
    final_form = service.forms().get(formId=form_id).execute()
    form_url = final_form.get("responderUri", f"https://docs.google.com/forms/d/{form_id}/viewform")

    logger.info(f"✅ Form updated successfully: {form_url}")

    return form_id, form_url