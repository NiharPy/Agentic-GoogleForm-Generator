from app.agents.executor.state import ExecutorState
from app.core.google_forms_client import GoogleFormsClient
import logging

logger = logging.getLogger(__name__)


async def execute_forms_api_node(state: ExecutorState) -> ExecutorState:
    """
    Node 3: Execute Google Forms API to create the form
    
    Steps:
    1. Create blank form
    2. Batch update with all questions
    3. Return form ID and URL
    
    Returns:
        Updated state with form_id and form_url
    """
    
    google_form_request = state.get("google_form_request")
    access_token = state.get("access_token")
    refresh_token = state.get("refresh_token")
    
    # Validation
    if not google_form_request:
        logger.error("No google_form_request in state")
        return {
            **state,
            "status": "failed",
            "error": "missing_google_form_request"
        }
    
    if not access_token or not refresh_token:
        logger.error("Missing Google credentials")
        return {
            **state,
            "status": "failed",
            "error": "missing_credentials"
        }
    
    try:
        # 1️⃣ Initialize Google Forms client
        forms_client = GoogleFormsClient(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        logger.info("🔧 Initialized Google Forms client")
        
        # 2️⃣ Create blank form
        title = google_form_request.get("title", "Untitled Form")
        
        logger.info(f"📝 Creating form: '{title}'")
        
        form_response = forms_client.create_form(
            title=title,
            document_title=title
        )
        
        form_id = form_response.get("formId")
        
        if not form_id:
            logger.error("No formId returned from create_form")
            return {
                **state,
                "status": "failed",
                "error": "no_form_id_returned"
            }
        
        logger.info(f"✅ Created form with ID: {form_id}")
        
        # 3️⃣ Batch update with questions
        requests = google_form_request.get("requests", [])
        
        if requests:
            logger.info(f"📤 Sending {len(requests)} batch update requests")
            
            update_response = forms_client.batch_update_form(
                form_id=form_id,
                requests=requests
            )
            
            logger.info(f"✅ Batch update completed")
        else:
            logger.warning("No requests to batch update (empty form)")
        
        # 4️⃣ Get final form
        final_form = forms_client.get_form(form_id)
        
        # Extract responder URI (the URL users fill out)
        responder_uri = final_form.get("responderUri", "")
        
        logger.info(f"✅ Form created successfully: {responder_uri}")
        
        # 5️⃣ Return success state
        return {
            **state,
            "form_id": form_id,
            "form_url": responder_uri,
            "status": "completed"
        }
    
    except Exception as e:
        logger.error(f"Failed to execute Google Forms API: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error": "api_execution_error",
            "details": str(e)
        }
