"""
Supabase service for user management and data storage.
Handles authentication, user profiles, and analysis history.
"""
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from config import Config

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for Supabase integration."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured")
        
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.service_client: Optional[Client] = None
        
        if Config.SUPABASE_SERVICE_ROLE_KEY:
            self.service_client = create_client(
                Config.SUPABASE_URL,
                Config.SUPABASE_SERVICE_ROLE_KEY
            )
        
        logger.info("SupabaseService initialized")
    
    def create_user_profile(
        self,
        user_id: str,
        email: str,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        campaign_role: Optional[str] = None,
        candidate_position: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        whatsapp_opt_in: bool = False
    ) -> Dict[str, Any]:
        """
        Create or update user profile.
        
        Args:
            user_id: Supabase user ID
            email: User email
            phone: Phone number
            first_name: First name
            last_name: Last name
            campaign_role: Role in campaign
            candidate_position: Position candidate is running for
            whatsapp_number: WhatsApp number
            whatsapp_opt_in: WhatsApp consent
            
        Returns:
            Profile data dictionary
        """
        try:
            profile_data = {
                'id': user_id,
                'email': email,
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name,
                'campaign_role': campaign_role,
                'candidate_position': candidate_position,
                'whatsapp_number': whatsapp_number,
                'whatsapp_opt_in': whatsapp_opt_in,
                'updated_at': 'now()'
            }
            
            # Remove None values
            profile_data = {k: v for k, v in profile_data.items() if v is not None}
            
            # Upsert profile (insert or update)
            result = self.client.table('profiles').upsert(profile_data).execute()
            
            logger.info(f"Profile created/updated for user: {user_id}")
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logger.error(f"Error creating user profile: {e}", exc_info=True)
            raise
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile data or None
        """
        try:
            result = self.client.table('profiles').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def save_analysis(
        self,
        user_id: str,
        location: str,
        theme: str,
        candidate_name: Optional[str],
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save analysis to database.
        
        Args:
            user_id: User ID
            location: Location analyzed
            theme: PND theme
            candidate_name: Candidate name
            analysis_data: Full analysis data
            
        Returns:
            Analysis ID or None
        """
        try:
            analysis_record = {
                'user_id': user_id,
                'location': location,
                'theme': theme,
                'candidate_name': candidate_name,
                'analysis_data': analysis_data,
                'created_at': 'now()'
            }
            
            result = self.client.table('analyses').insert(analysis_record).execute()
            
            if result.data:
                analysis_id = result.data[0].get('id')
                logger.info(f"Analysis saved: {analysis_id}")
                return analysis_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error saving analysis: {e}", exc_info=True)
            return None
    
    def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's analysis history.
        
        Args:
            user_id: User ID
            limit: Maximum number of analyses to return
            
        Returns:
            List of analysis records
        """
        try:
            result = (
                self.client.table('analyses')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .limit(limit)
                .execute()
            )
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting user analyses: {e}")
            return []
    
    def update_whatsapp_consent(
        self,
        user_id: str,
        whatsapp_opt_in: bool,
        whatsapp_number: Optional[str] = None
    ) -> bool:
        """
        Update WhatsApp consent for user.
        
        Args:
            user_id: User ID
            whatsapp_opt_in: Consent status
            whatsapp_number: WhatsApp number
            
        Returns:
            True if successful
        """
        try:
            update_data = {
                'whatsapp_opt_in': whatsapp_opt_in,
                'updated_at': 'now()'
            }
            
            if whatsapp_number:
                update_data['whatsapp_number'] = whatsapp_number
            
            self.client.table('profiles').update(update_data).eq('id', user_id).execute()
            
            logger.info(f"WhatsApp consent updated for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating WhatsApp consent: {e}")
            return False

