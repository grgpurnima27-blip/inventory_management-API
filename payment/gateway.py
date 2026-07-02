import requests
from django.conf import settings


class KhaltiGateway:
    """
    Khalti Payment Gateway Integration.
    """

    INITIATE_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
    LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"

    @staticmethod
    def get_headers():
        return {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @classmethod
    def initiate_payment(
        cls,
        order,
        amount,
        purchase_order_id,
        purchase_order_name,
        return_url,
        website_url,
    ):
        """
        Initiate Khalti payment.
        """

        payload = {
            "return_url": return_url,
            "website_url": website_url,
            "amount": int(amount * 100),  # Khalti expects paisa
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": purchase_order_name,
        }

        response = requests.post(
            cls.INITIATE_URL,
            json=payload,
            headers=cls.get_headers(),
            timeout=30,
        )

        return response.json()

    @classmethod
    def verify_payment(cls, pidx):
        """
        Verify Khalti payment.
        """

        response = requests.post(
            cls.LOOKUP_URL,
            json={"pidx": pidx},
            headers=cls.get_headers(),
            timeout=30,
        )

        return response.json()
    
class EsewaGateway:
    """
    eSewa Integration.
    """

    @staticmethod
    def initiate_payment(
        amount,
        transaction_uuid,
        product_code,
        success_url,
        failure_url,
    ):
        """
        Generate eSewa payment payload.
        """

        return {
            "amount": amount,
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "success_url": success_url,
            "failure_url": failure_url,
        }

    @staticmethod
    def verify_payment(data):
        """
        Placeholder.

        eSewa verification implementation
        will be added later.
        """

        return data