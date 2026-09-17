# -*- coding: utf-8 -*-

"""
SMS Notification Service
Integrates with Twilio to send automated repair status updates to customers.
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any

from src.utils.logger import logger

class SMSService:
    """
    SMS notification service for customer updates.
    Uses Twilio API for message delivery.
    """
    
    def __init__(self, db):
        self.db = db
        self.enabled = False
        self.twilio_client = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Twilio credentials from database settings."""
        try:
            account_sid = self.db.get_setting("twilio_account_sid", "")
            auth_token = self.db.get_setting("twilio_auth_token", "")
            from_number = self.db.get_setting("twilio_from_number", "")
            
            if account_sid and auth_token and from_number:
                try:
                    from twilio.rest import Client
                    self.twilio_client = Client(account_sid, auth_token)
                    self.from_number = from_number
                    self.enabled = True
                except ImportError:
                    logger.warning("Twilio library not installed. Run: pip install twilio")
                    self.enabled = False
                except Exception as e:
                    logger.error("Twilio initialization error: %s", e)
                    self.enabled = False
        except Exception as e:
            logger.error("SMS service initialization error: %s", e)
            self.enabled = False
    
    def send_status_update(self, tracking_no: str, status: str, customer_phone: str) -> bool:
        """
        Send status update SMS to customer.
        
        Args:
            tracking_no: Device tracking number
            status: New status (e.g., "Beklemede", "Tamirde", "Hazır")
            customer_phone: Customer's phone number
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        if not customer_phone or len(customer_phone) < 10:
            return False
        
        # Get message template from database
        template = self._get_template(status)
        if not template:
            return False
        
        # Format message
        company_name = self.db.get_setting("company_name", "Bulut Teknik")
        message = template.format(
            tracking_no=tracking_no,
            status=status,
            company_name=company_name
        )
        
        try:
            # Ensure phone number is in E.164 format
            formatted_phone = self._format_phone_number(customer_phone)
            
            # Send SMS via Twilio
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=self.from_number,
                to=formatted_phone
            )
            
            # Log the SMS in database
            self._log_sms(tracking_no, customer_phone, message, message_obj.sid)
            
            return True
        except Exception as e:
            logger.error("SMS send error: %s", e)
            self._log_sms(tracking_no, customer_phone, message, f"ERROR: {str(e)}")
            return False
    
    def _get_template(self, status: str) -> Optional[str]:
        """Get SMS template for given status."""
        templates = {
            "Beklemede": "{company_name}: Cihazınız (#{tracking_no}) alındı ve inceleme bekliyor. Bilgi: 0534 878 10 47",
            "Tamirde": "{company_name}: Cihazınız (#{tracking_no}) tamir aşamasında. İlerlemeden haberdar edileceksiniz.",
            "Test Aşaması": "{company_name}: Cihazınız (#{tracking_no}) test ediliyor. Yakında tamamlanacak.",
            "Onay Bekliyor": "{company_name}: Cihazınız (#{tracking_no}) için tamir onayınız bekleniyor. Lütfen arayın: 0534 878 10 47",
            "Hazır": "{company_name}: Cihazınız (#{tracking_no}) hazır! Teslim alabilirsiniz. Çalışma saatleri: 09:00-18:00"
        }
        
        # Check for custom template in database
        custom_template = self.db.get_setting(f"sms_template_{status}", "")
        if custom_template:
            return custom_template
        
        return templates.get(status, None)
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number to E.164 format (+90XXXXXXXXXX).
        
        Args:
            phone: Phone number in various formats
            
        Returns:
            E.164 formatted phone number
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Handle Turkish numbers
        if digits.startswith('0'):
            digits = '90' + digits[1:]  # Replace leading 0 with 90
        elif not digits.startswith('90'):
            digits = '90' + digits  # Add country code
        
        return '+' + digits
    
    def _log_sms(self, tracking_no: str, phone: str, message: str, sid: str):
        """Log SMS activity to database."""
        try:
            self.db.cursor.execute("""
                INSERT INTO sms_log (tracking_no, phone, message, twilio_sid, sent_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tracking_no, phone, message, sid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.db.conn.commit()
        except Exception as e:
            logger.error("SMS log error: %s", e)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Twilio connection and return status.
        
        Returns:
            Dictionary with status and message
        """
        if not self.enabled:
            return {"status": "error", "message": "SMS service not configured"}
        
        try:
            # Test by fetching account info
            account = self.twilio_client.api.accounts(self.twilio_client.account_sid).fetch()
            return {
                "status": "success",
                "message": f"Connected to Twilio account: {account.friendly_name}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
