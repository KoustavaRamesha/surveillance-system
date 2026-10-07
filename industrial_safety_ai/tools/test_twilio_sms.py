"""
CLI utility to test Twilio SMS connectivity and configuration.
Usage:
    python tools/test_twilio_sms.py
    python tools/test_twilio_sms.py --to +1234567890 --from +0987654321
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.sms_notifier import send_test_sms, _get_auth
import requests


def check_account_status() -> None:
    auth, sid = _get_auth()
    api_key = config.TWILIO_API_KEY_SID
    token = config.TWILIO_AUTH_TOKEN
    
    print("=" * 60)
    print("Checking Twilio Configuration...")
    print(f"Account SID:    {sid}")
    if api_key:
        print(f"API Key SID:    {api_key} (Active)")
    print(f"Auth Token:     {'*' * (len(token) - 4) + token[-4:] if token else 'None'}")
    
    # Check messages endpoint with active auth
    msg_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        r = requests.get(msg_url, auth=auth, timeout=10)
        if r.status_code == 200:
            print("Twilio Auth:    [OK] Validated successfully (Messages API accessible)")
        else:
            print(f"Twilio Auth:    [FAILED] Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Network error:  {e}")

    # Check incoming phone numbers
    in_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json"
    try:
        r = requests.get(in_url, auth=auth, timeout=10)
        if r.status_code == 200:
            numbers = r.json().get("incoming_phone_numbers", [])
            if numbers:
                print("\nProvisioned Twilio Numbers:")
                for n in numbers:
                    print(f"  - {n.get('phone_number')} ({n.get('friendly_name')})")
            else:
                print("\nProvisioned Twilio Numbers: None found.")
                print("Tip: Claim a phone number in your Twilio Console (click 'Get a phone number').")
    except Exception as e:
        print(f"Error checking phone numbers: {e}")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Twilio SMS notification for safety alerts.")
    parser.add_argument("--to", help="Recipient phone number (e.g., +1234567890)", default=None)
    parser.add_argument("--from", dest="from_num", help="Twilio sender phone number", default=None)
    parser.add_argument("--message", default="[ALERT] Restricted Area Intrusion detected on Camera 1 (Zone: Warehouse).", help="SMS body")
    args = parser.parse_args()

    check_account_status()

    to_num = args.to or config.TWILIO_TO_NUMBER
    from_num = args.from_num or config.TWILIO_FROM_NUMBER

    if not to_num or not from_num:
        print("\nNote: TWILIO_FROM_NUMBER or TWILIO_TO_NUMBER is not yet configured.")
        print("To send a live test SMS, run:")
        print("    python tools/test_twilio_sms.py --to <YOUR_PHONE_NUMBER> --from <TWILIO_NUMBER>")
        print("or set them in industrial_safety_ai/.env")
        return

    print(f"\nSending test alert to {to_num} from {from_num}...")
    res = send_test_sms(to_number=to_num, from_number=from_num, message=args.message)
    if res["success"]:
        print(f"[SUCCESS] SMS sent successfully! Twilio SID: {res['sid']}")
    else:
        print(f"[ERROR] Failed to send SMS: {res['error']}")


if __name__ == "__main__":
    main()
