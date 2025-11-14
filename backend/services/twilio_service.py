"""
Twilio WhatsApp service for sending reports.
Handles WhatsApp message sending with approved templates.
"""
import json
import logging
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from config import Config
from models.schemas import Speech, StrategicPlan

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for Twilio WhatsApp integration."""
    
    def __init__(self):
        """Initialize Twilio client."""
        if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured. WhatsApp sending will be disabled.")
            self.client = None
        else:
            self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
            logger.info("TwilioService initialized")
    
    def send_whatsapp_report(
        self,
        phone_number: str,
        recipient_name: str,
        candidate_name: str,
        speech: Speech,
        strategic_plan: StrategicPlan,
        location: str
    ) -> Dict[str, Any]:
        """
        Send analysis report via WhatsApp using approved template.
        
        Args:
            phone_number: Recipient phone number (format: +573001234567)
            recipient_name: Name of recipient
            candidate_name: Candidate name
            speech: Speech object
            strategic_plan: StrategicPlan object
            location: Location analyzed
            
        Returns:
            Dictionary with success status and message SID
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Twilio not configured'
            }
        
        try:
            # Format phone number
            if not phone_number.startswith('whatsapp:'):
                if not phone_number.startswith('+'):
                    phone_number = f"+{phone_number}"
                phone_number = f"whatsapp:{phone_number}"
            
            # Prepare content variables for template
            # Note: WhatsApp templates have character limits
            speech_preview = speech.content[:300] + "..." if len(speech.content) > 300 else speech.content
            plan_preview = str(strategic_plan.objectives[:2])[:200] if strategic_plan.objectives else ""
            
            # Try to send with approved template first
            try:
                message = self.client.messages.create(
                    from_=Config.TWILIO_WHATSAPP_FROM,
                    to=phone_number,
                    content_sid=Config.TWILIO_CONTENT_SID,
                    content_variables=json.dumps({
                        "1": recipient_name,
                        "2": candidate_name,
                        "3": location,
                        "4": speech_preview,
                        "5": plan_preview
                    })
                )
                
                logger.info(f"WhatsApp message sent successfully: {message.sid}")
                return {
                    'success': True,
                    'message_sid': message.sid,
                    'status': message.status
                }
                
            except TwilioRestException as e:
                # If template fails, try fallback text message
                logger.warning(f"Template send failed, trying fallback: {e}")
                return self._send_fallback_message(
                    phone_number,
                    recipient_name,
                    candidate_name,
                    speech,
                    strategic_plan,
                    location
                )
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_fallback_message(
        self,
        phone_number: str,
        recipient_name: str,
        candidate_name: str,
        speech: Speech,
        strategic_plan: StrategicPlan,
        location: str
    ) -> Dict[str, Any]:
        """Send fallback text message if template fails."""
        try:
            message_body = f"""*CASTOR ELECCIONES - Reporte de Análisis*

Hola {recipient_name},

Análisis completado para {location} - Candidato: {candidate_name}

*Discurso:*
{speech.content[:500]}...

*Plan Estratégico:*
{chr(10).join(f"• {obj}" for obj in strategic_plan.objectives[:3])}

Para el reporte completo, visita la plataforma CASTOR ELECCIONES.

---
Generado por CASTOR ELECCIONES"""

            message = self.client.messages.create(
                from_=Config.TWILIO_WHATSAPP_FROM,
                to=phone_number,
                body=message_body
            )
            
            logger.info(f"Fallback WhatsApp message sent: {message.sid}")
            return {
                'success': True,
                'message_sid': message.sid,
                'status': message.status,
                'fallback': True
            }
            
        except Exception as e:
            logger.error(f"Error sending fallback message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid format
        """
        # Remove whatsapp: prefix if present
        cleaned = phone_number.replace('whatsapp:', '').strip()
        
        # Basic validation: should start with + and have 10-15 digits
        if not cleaned.startswith('+'):
            return False
        
        digits = cleaned[1:].replace(' ', '').replace('-', '')
        return len(digits) >= 10 and len(digits) <= 15 and digits.isdigit()

