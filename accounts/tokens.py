import hashlib
import hmac
import time
import base64
from django.conf import settings


def generate_token(user_id: int, token_type: str) -> str:
    """Generate a secure token for email verification or password reset."""
    timestamp = str(int(time.time()))
    message = f"{user_id}:{token_type}:{timestamp}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    token_data = f"{message}:{signature}"
    return base64.urlsafe_b64encode(token_data.encode()).decode()


def verify_token(token: str, token_type: str, max_age_seconds: int = 86400) -> int | None:
    """
    Verify a token and return the user_id if valid, else None.
    Default max_age is 24 hours (86400 seconds).
    """
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, t_type, timestamp, signature = decoded.rsplit(':', 3)

        # Check token type
        if t_type != token_type:
            return None

        # Check expiry
        if int(time.time()) - int(timestamp) > max_age_seconds:
            return None

        # Verify signature
        message = f"{user_id}:{t_type}:{timestamp}"
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        return int(user_id)

    except Exception:
        return None