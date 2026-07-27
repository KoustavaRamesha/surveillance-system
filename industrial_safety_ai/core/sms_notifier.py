import logging

logger = logging.getLogger("sms_notifier")

def send_sms_alert(message: str) -> None:
    """
    Mock implementation of an SMS alert sender.
    In a real production environment, this would integrate with Twilio, AWS SNS, etc.
    """
    # Simply log it to the console with a prominent prefix for now.
    alert_text = f"\n{'='*50}\n[SMS DISPATCHED]: {message}\n{'='*50}\n"
    print(alert_text)
    logger.info("SMS DISPATCHED: %s", message)
