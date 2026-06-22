"""Mock notification service. Interface ready for Twilio/MSG91 integration."""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.is_mock = settings.sms_provider_key == "mock"

    async def send_otp_sms(self, phone: str, otp: str) -> bool:
        if self.is_mock:
            logger.info(f"[MOCK SMS] OTP {otp} sent to {phone}")
            return True
        # TODO: Integrate Twilio/MSG91
        # client = Client(account_sid, auth_token)
        # client.messages.create(to=phone, from_="+1...", body=f"Your OTP: {otp}")
        return False

    async def send_appointment_confirmation(self, phone: str, patient_name: str, doctor_name: str, slot_time: str) -> bool:
        message = f"Dear {patient_name}, your appointment with {doctor_name} is confirmed for {slot_time}. Join via the app."
        if self.is_mock:
            logger.info(f"[MOCK SMS] Confirmation to {phone}: {message}")
            return True
        return False

    async def send_appointment_reminder(self, phone: str, patient_name: str, doctor_name: str, slot_time: str) -> bool:
        message = f"Reminder: {patient_name}, your teleconsult with {doctor_name} is at {slot_time}. Join on time!"
        if self.is_mock:
            logger.info(f"[MOCK SMS] Reminder to {phone}: {message}")
            return True
        return False

    async def send_prescription_ready(self, phone: str, patient_name: str) -> bool:
        message = f"Dear {patient_name}, your prescription is ready. View it in the app."
        if self.is_mock:
            logger.info(f"[MOCK SMS] Prescription ready to {phone}: {message}")
            return True
        return False

    async def send_whatsapp(self, phone: str, message: str) -> bool:
        if self.is_mock:
            logger.info(f"[MOCK WhatsApp] to {phone}: {message}")
            return True
        return False


notification_service = NotificationService()
