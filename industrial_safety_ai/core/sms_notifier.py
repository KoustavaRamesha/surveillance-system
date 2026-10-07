from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Tuple
import requests

import config

logger = logging.getLogger("sms_notifier")


def _get_auth() -> Tuple[Optional[Tuple[str, str]], str]:
    """
    Get HTTP Basic Auth credentials and Account SID.
    Prefers API Key (SK...) + API Secret if available, else Account SID (AC...) + Auth Token.
    """
    account_sid = getattr(config, "TWILIO_ACCOUNT_SID", "").strip()
    api_key_sid = getattr(config, "TWILIO_API_KEY_SID", "").strip()
    api_key_secret = getattr(config, "TWILIO_API_KEY_SECRET", "").strip()
    auth_token = getattr(config, "TWILIO_AUTH_TOKEN", "").strip()

    if api_key_sid and api_key_secret:
        return (api_key_sid, api_key_secret), account_sid
    elif account_sid and auth_token:
        return (account_sid, auth_token), account_sid
    return None, account_sid


def _dispatch_twilio_request(
    auth: Tuple[str, str],
    account_sid: str,
    from_number: str,
    to_number: str,
    message: str,
) -> Dict[str, Any]:
    """Execute synchronous POST to Twilio Messages API."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = {
        "From": from_number,
        "To": to_number,
        "Body": message,
    }
    try:
        response = requests.post(
            url,
            data=payload,
            auth=auth,
            timeout=10,
        )
        if response.status_code in (200, 201):
            data = response.json()
            sid = data.get("sid", "UNKNOWN_SID")
            logger.info("Twilio SMS sent successfully! SID: %s | To: %s", sid, to_number)
            print(f"\n{'='*55}\n[TWILIO SMS SENT]\nSID: {sid}\nTo: {to_number}\nMessage: {message}\n{'='*55}\n")
            return {"success": True, "status_code": response.status_code, "sid": sid, "error": None}
        else:
            err_data = {}
            try:
                err_data = response.json()
            except Exception:
                pass
            err_msg = err_data.get("message", response.text)
            logger.error("Twilio SMS failed. Status: %s, Message: %s", response.status_code, err_msg)
            print(f"\n{'='*55}\n[TWILIO SMS ERROR]\nStatus: {response.status_code}\nDetail: {err_msg}\n{'='*55}\n")
            return {"success": False, "status_code": response.status_code, "sid": None, "error": err_msg}
    except requests.RequestException as exc:
        logger.error("Twilio SMS network exception: %s", exc)
        print(f"\n{'='*55}\n[TWILIO SMS NETWORK ERROR]: {exc}\n{'='*55}\n")
        return {"success": False, "status_code": 0, "sid": None, "error": str(exc)}


def send_sms_alert(message: str, async_send: bool = True) -> bool:
    """
    Send an SMS alert via Twilio for critical safety events (e.g., restricted area intrusions).

    If TWILIO_SMS_ENABLED is False or credentials/phone numbers are unconfigured,
    logs the alert simulation without raising errors.
    If async_send is True, dispatches the HTTP request in a background thread to prevent
    blocking the video capture and inference pipelines.
    """
    if not getattr(config, "TWILIO_SMS_ENABLED", True):
        logger.debug("Twilio SMS dispatch is disabled in config.")
        return False

    auth, account_sid = _get_auth()
    from_number = getattr(config, "TWILIO_FROM_NUMBER", "").strip()
    to_number = getattr(config, "TWILIO_TO_NUMBER", "").strip()

    # If sender or recipient phone numbers are not configured yet
    if not from_number or not to_number:
        banner = (
            f"\n{'='*65}\n"
            f"[SMS SIMULATION (TWILIO CREDENTIALS LOADED)]:\n"
            f"Notice: Set TWILIO_FROM_NUMBER and TWILIO_TO_NUMBER in .env to send real SMS.\n"
            f"Message: {message}\n"
            f"{'='*65}\n"
        )
        print(banner)
        logger.warning(
            "Twilio credentials found, but TWILIO_FROM_NUMBER or TWILIO_TO_NUMBER is missing. "
            "Simulating SMS alert: %s",
            message,
        )
        return False

    if not auth or not account_sid:
        logger.warning("Twilio credentials missing. Cannot dispatch SMS.")
        return False

    if async_send:
        worker_thread = threading.Thread(
            target=_dispatch_twilio_request,
            args=(auth, account_sid, from_number, to_number, message),
            daemon=True,
            name="TwilioSmsDispatcher",
        )
        worker_thread.start()
        return True
    else:
        result = _dispatch_twilio_request(auth, account_sid, from_number, to_number, message)
        return bool(result.get("success"))


def send_test_sms(
    to_number: Optional[str] = None,
    from_number: Optional[str] = None,
    message: str = "Test intrusion alert from Industrial Safety AI system",
) -> Dict[str, Any]:
    """Synchronously test Twilio SMS dispatch for configuration verification."""
    auth, account_sid = _get_auth()
    from_num = (from_number or getattr(config, "TWILIO_FROM_NUMBER", "")).strip()
    to_num = (to_number or getattr(config, "TWILIO_TO_NUMBER", "")).strip()

    if not auth or not account_sid:
        return {"success": False, "status_code": 0, "sid": None, "error": "Missing Twilio credentials"}
    if not from_num or not to_num:
        return {"success": False, "status_code": 0, "sid": None, "error": "Both sender and recipient phone numbers are required"}

    return _dispatch_twilio_request(auth, account_sid, from_num, to_num, message)


test_send_sms = send_test_sms
