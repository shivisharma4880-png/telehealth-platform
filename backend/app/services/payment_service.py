"""Mock payment service. Interface ready for Razorpay integration."""
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        self.is_mock = settings.razorpay_key_id == "mock"

    async def create_order(self, amount: float, currency: str = "INR", appointment_id: str = "") -> dict:
        """Create a payment order. Returns order details."""
        if self.is_mock:
            order_id = f"mock_order_{uuid.uuid4().hex[:12]}"
            logger.info(f"[MOCK PAYMENT] Created order {order_id} for ₹{amount}")
            return {
                "order_id": order_id,
                "amount": int(amount * 100),  # paise
                "currency": currency,
                "status": "created",
                "key_id": settings.razorpay_key_id,
            }
        # TODO: Integrate Razorpay
        # import razorpay
        # client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
        # order = client.order.create({"amount": int(amount * 100), "currency": currency})
        # return order
        raise NotImplementedError("Razorpay integration not configured")

    async def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        """Verify payment signature."""
        if self.is_mock:
            logger.info(f"[MOCK PAYMENT] Verified payment {payment_id}")
            return True
        # TODO: Verify HMAC signature with Razorpay
        return False

    async def refund(self, payment_id: str, amount: float) -> dict:
        """Process refund."""
        if self.is_mock:
            refund_id = f"mock_refund_{uuid.uuid4().hex[:12]}"
            logger.info(f"[MOCK PAYMENT] Refund {refund_id} for ₹{amount}")
            return {"refund_id": refund_id, "status": "processed", "amount": amount}
        raise NotImplementedError("Razorpay refund not configured")


payment_service = PaymentService()
