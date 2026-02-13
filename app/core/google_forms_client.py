# app/core/google_forms_client.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Any, Optional, List
import logging
from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class GoogleFormsClient:
    """Client for Google Forms API"""
    
    def __init__(self, access_token: str, refresh_token: str):
        """
        Initialize Google Forms client
        
        Args:
            access_token: User's access token
            refresh_token: User's refresh token
        """
        self.settings = get_settings()
        
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.GOOGLE_CLIENT_ID,
            client_secret=self.settings.GOOGLE_CLIENT_SECRET
        )
        
        self.service = build('forms', 'v1', credentials=self.credentials)
    
    def create_form(self, title: str, document_title: str = None) -> Dict[str, Any]:
        """
        Create a new Google Form
        
        Args:
            title: Form title
            document_title: Document title (defaults to form title)
            
        Returns:
            Created form response
        """
        try:
            form = {
                "info": {
                    "title": title,
                    "documentTitle": document_title or title
                }
            }
            
            result = self.service.forms().create(body=form).execute()
            logger.info(f"Created form: {result.get('formId')}")
            
            return result
            
        except HttpError as e:
            logger.error(f"Failed to create form: {str(e)}")
            raise
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """
        Get form by ID
        
        Args:
            form_id: Google Form ID
            
        Returns:
            Form data
        """
        try:
            result = self.service.forms().get(formId=form_id).execute()
            return result
        except HttpError as e:
            logger.error(f"Failed to get form {form_id}: {str(e)}")
            raise
    
    def batch_update_form(
        self,
        form_id: str,
        requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update form
        
        Args:
            form_id: Google Form ID
            requests: List of update requests
            
        Returns:
            Update response
        """
        try:
            body = {"requests": requests}
            result = self.service.forms().batchUpdate(
                formId=form_id,
                body=body
            ).execute()
            
            logger.info(f"Updated form {form_id} with {len(requests)} requests")
            return result
            
        except HttpError as e:
            logger.error(f"Failed to update form {form_id}: {str(e)}")
            raise


def get_google_forms_client(access_token: str, refresh_token: str) -> GoogleFormsClient:
    """
    Create Google Forms client for user
    
    Args:
        access_token: User's access token
        refresh_token: User's refresh token
        
    Returns:
        GoogleFormsClient instance
    """
    return GoogleFormsClient(access_token, refresh_token)