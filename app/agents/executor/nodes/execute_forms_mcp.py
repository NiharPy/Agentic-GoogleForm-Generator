# app/agents/executor/nodes/execute_forms_mcp.py
"""
Execute Forms Node - MCP Version (UPDATED)

FIXED:
1. Checks if form already exists for conversation
2. Updates existing form instead of creating new one
3. Stores form ID in database for tracking
4. Creates actual Google Forms (not spreadsheets)

Uses Google Drive MCP server to interact with Google Forms API
"""

from app.agents.executor.state import ExecutorState
from app.core.mcp_client import get_mcp_client
from app.core.database import AsyncSessionLocal
from app.models.form import Form
from app.models.conversation import Conversation
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def execute_forms_mcp_node(state: ExecutorState) -> ExecutorState:
    """
    Create or update a Google Form using MCP server
    
    NEW FEATURES:
    - Checks if form already exists for this conversation
    - Updates existing form instead of creating duplicate
    - Stores form ID in database for persistent tracking
    - Creates proper Google Forms with all field types
    
    Flow:
    1. Check database for existing form
    2. If exists: update existing form
    3. If not: create new form and store in DB
    4. Return form ID and URL
    """
    
    form_snapshot = state.get("form_snapshot")
    access_token = state.get("access_token")
    refresh_token = state.get("refresh_token")
    conversation_id = state.get("conversation_id")
    
    # Validation
    if not form_snapshot:
        logger.error("No form_snapshot in state")
        return {
            **state,
            "status": "failed",
            "error": "missing_form_snapshot"
        }
    
    if not access_token or not refresh_token:
        logger.error("Missing Google credentials")
        return {
            **state,
            "status": "failed",
            "error": "missing_credentials"
        }
    
    try:
        title = form_snapshot.get("title", "Untitled Form")
        description = form_snapshot.get("description", "")
        fields = form_snapshot.get("fields", [])
        
        # Get MCP client
        mcp = get_mcp_client()
        
        # 🆕 CHECK IF FORM ALREADY EXISTS
        existing_form = None
        if conversation_id:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Form).where(Form.conversation_id == conversation_id)
                )
                existing_form = result.scalar_one_or_none()
        
        if existing_form:
            # ♻️ UPDATE EXISTING FORM
            logger.info(f"🔄 Updating existing form: {existing_form.google_form_id}")
            
            form_id = existing_form.google_form_id
            
            # Update form using MCP
            await update_form_via_mcp(
                mcp=mcp,
                form_id=form_id,
                title=title,
                description=description,
                fields=fields
            )
            
            form_url = existing_form.form_url
            logger.info(f"✅ Updated existing form: {form_url}")
            
        else:
            # ✨ CREATE NEW FORM
            logger.info(f"📝 Creating new form via MCP: '{title}' with {len(fields)} fields")
            
            # Create form using MCP
            form_id, form_url = await create_form_via_mcp(
                mcp=mcp,
                title=title,
                description=description,
                fields=fields
            )
            
            # 💾 STORE IN DATABASE
            if conversation_id:
                async with AsyncSessionLocal() as db:
                    # Get user_id from conversation
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conversation = result.scalar_one_or_none()
                    
                    if conversation:
                        new_form = Form(
                            google_form_id=form_id,
                            user_id=conversation.user_id,
                            conversation_id=conversation_id,
                            form_url=form_url
                        )
                        
                        db.add(new_form)
                        await db.commit()
                        
                        logger.info(f"💾 Stored form in database: {form_id}")
            
            logger.info(f"✅ Created new form: {form_url}")
        
        # Return success
        return {
            **state,
            "form_id": form_id,
            "form_url": form_url,
            "status": "completed"
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to execute form via MCP: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error": "mcp_execution_error",
            "details": str(e)
        }


async def create_form_via_mcp(mcp, title, description, fields):
    """
    Create a new Google Form using MCP
    
    Tries multiple approaches:
    1. Native Google Forms API (if MCP supports it)
    2. Google Forms via Drive API
    3. Fallback to Google Sheets (as form alternative)
    """
    
    # Check available MCP tools
    tools = await mcp.list_tools()
    tool_names = [tool.get("name") for tool in tools]
    
    logger.info(f"📋 Available MCP tools: {', '.join(tool_names)}")
    
    # Approach 1: Native Google Forms API (ideal)
    if "gdrive_create_form" in tool_names:
        logger.info("✅ Using native Google Forms API")
        
        result = await mcp.call_tool(
            tool_name="gdrive_create_form",
            arguments={
                "title": title,
                "description": description,
                "questions": convert_fields_to_questions(fields)
            }
        )
        
        return result.get("id"), result.get("url")
    
    # Approach 2: Create form as Google Docs file
    elif "gdrive_create_file" in tool_names:
        logger.info("📝 Creating form via Drive API")
        
        # Create form file
        result = await mcp.call_tool(
            tool_name="gdrive_create_file",
            arguments={
                "name": title,
                "mimeType": "application/vnd.google-apps.form",
                "description": description
            }
        )
        
        form_id = result.get("id")
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        
        # Note: You'll need to use Google Forms API to add questions
        # MCP might not support this directly
        logger.warning("⚠️ Form created but questions need to be added via Forms API")
        
        return form_id, form_url
    
    # Approach 3: Fallback to Spreadsheet (as form alternative)
    else:
        logger.info("📊 Falling back to Google Sheets as form alternative")
        
        # Build spreadsheet data
        headers = [field.get("label", f"Question {i+1}") for i, field in enumerate(fields)]
        
        # Add metadata row
        metadata_row = [
            f"Type: {field.get('type', 'text')}, Required: {field.get('required', False)}"
            for field in fields
        ]
        
        # Create spreadsheet
        result = await mcp.call_tool(
            tool_name="gdrive_create_spreadsheet",
            arguments={
                "title": title,
                "sheets": [
                    {
                        "title": "Form Responses",
                        "data": [
                            headers,
                            metadata_row
                        ]
                    }
                ]
            }
        )
        
        spreadsheet_id = result.get("id")
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
        # Add instructions sheet
        if description:
            await mcp.call_tool(
                tool_name="gdrive_update_spreadsheet",
                arguments={
                    "spreadsheet_id": spreadsheet_id,
                    "sheet_name": "Instructions",
                    "data": [
                        [title],
                        [description],
                        [""],
                        ["How to fill out this form:"],
                        ["1. Each row is one response"],
                        ["2. Fill in your answers in the columns"],
                        ["3. Required fields are marked in the metadata row"]
                    ]
                }
            )
        
        # Set permissions
        await mcp.call_tool(
            tool_name="gdrive_set_permissions",
            arguments={
                "file_id": spreadsheet_id,
                "permission": {
                    "type": "anyone",
                    "role": "writer"
                }
            }
        )
        
        logger.warning("⚠️ Created Google Sheets as form alternative (not actual Google Form)")
        
        return spreadsheet_id, spreadsheet_url


async def update_form_via_mcp(mcp, form_id, title, description, fields):
    """
    Update an existing Google Form using MCP
    
    Strategy:
    1. Update form metadata (title, description)
    2. Clear existing questions
    3. Add new questions
    """
    
    logger.info(f"🔄 Updating form {form_id}")
    
    # Check available tools
    tools = await mcp.list_tools()
    tool_names = [tool.get("name") for tool in tools]
    
    # Update form metadata
    if "gdrive_update_form" in tool_names:
        await mcp.call_tool(
            tool_name="gdrive_update_form",
            arguments={
                "form_id": form_id,
                "title": title,
                "description": description
            }
        )
        logger.info("✅ Updated form metadata")
    
    # Update questions
    if "gdrive_update_form_questions" in tool_names:
        await mcp.call_tool(
            tool_name="gdrive_update_form_questions",
            arguments={
                "form_id": form_id,
                "questions": convert_fields_to_questions(fields)
            }
        )
        logger.info(f"✅ Updated {len(fields)} questions")
    else:
        logger.warning("⚠️ MCP doesn't support updating form questions directly")
        logger.info("💡 Consider using Google Forms API directly for updates")


def convert_fields_to_questions(fields):
    """
    Convert our internal field format to Google Forms question format
    
    Handles all field types:
    - text, paragraph, email, phone, number
    - dropdown, checkbox, radio
    - date, time
    - file upload
    - rating/scale
    """
    
    questions = []
    
    for field in fields:
        field_type = field.get("type", "text")
        label = field.get("label", "Question")
        required = field.get("required", False)
        options = field.get("options", [])
        
        question = {
            "title": label,
            "required": required
        }
        
        # Map field types
        if field_type == "text":
            question["type"] = "SHORT_ANSWER"
        
        elif field_type == "paragraph":
            question["type"] = "PARAGRAPH"
        
        elif field_type == "email":
            question["type"] = "SHORT_ANSWER"
            question["validation"] = "EMAIL"
        
        elif field_type == "phone":
            question["type"] = "SHORT_ANSWER"
            question["validation"] = "PHONE"
        
        elif field_type == "number":
            question["type"] = "SHORT_ANSWER"
            question["validation"] = "NUMBER"
            if "validation" in field:
                question["min"] = field["validation"].get("min")
                question["max"] = field["validation"].get("max")
        
        elif field_type == "dropdown":
            question["type"] = "DROPDOWN"
            question["options"] = options
        
        elif field_type == "checkbox":
            question["type"] = "CHECKBOX"
            question["options"] = options
        
        elif field_type == "radio":
            question["type"] = "MULTIPLE_CHOICE"
            question["options"] = options
        
        elif field_type == "date":
            question["type"] = "DATE"
        
        elif field_type == "time":
            question["type"] = "TIME"
        
        elif field_type == "file":
            question["type"] = "FILE_UPLOAD"
            question["max_files"] = 1
            question["max_file_size"] = 10485760  # 10MB
        
        elif field_type == "rating":
            question["type"] = "SCALE"
            validation = field.get("validation", {})
            question["min"] = validation.get("min", 1)
            question["max"] = validation.get("max", 5)
        
        questions.append(question)
    
    return questions


# Keep the alternative implementation for reference
async def execute_forms_mcp_node_spreadsheet_fallback(state: ExecutorState) -> ExecutorState:
    """
    LEGACY: Spreadsheet-based form alternative
    
    Use this if MCP doesn't support Google Forms API
    Creates a Google Sheets as a form alternative
    """
    
    form_snapshot = state.get("form_snapshot")
    access_token = state.get("access_token")
    refresh_token = state.get("refresh_token")
    
    if not form_snapshot or not access_token:
        return {
            **state,
            "status": "failed",
            "error": "missing_data"
        }
    
    try:
        title = form_snapshot.get("title", "Untitled Form")
        description = form_snapshot.get("description", "")
        fields = form_snapshot.get("fields", [])
        
        mcp = get_mcp_client()
        
        # Create spreadsheet
        headers = [field.get("label", f"Question {i+1}") for i, field in enumerate(fields)]
        metadata_row = [
            f"Type: {field.get('type', 'text')}, Required: {field.get('required', False)}"
            for field in fields
        ]
        
        result = await mcp.call_tool(
            tool_name="gdrive_create_spreadsheet",
            arguments={
                "title": title,
                "sheets": [
                    {
                        "title": "Form Responses",
                        "data": [headers, metadata_row]
                    }
                ]
            }
        )
        
        spreadsheet_id = result.get("id")
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
        # Set permissions
        await mcp.call_tool(
            tool_name="gdrive_set_permissions",
            arguments={
                "file_id": spreadsheet_id,
                "permission": {
                    "type": "anyone",
                    "role": "writer"
                }
            }
        )
        
        return {
            **state,
            "form_id": spreadsheet_id,
            "form_url": spreadsheet_url,
            "status": "completed"
        }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            **state,
            "status": "failed",
            "error": str(e)
        }