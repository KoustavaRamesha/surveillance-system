from unittest.mock import MagicMock, patch
import pytest

from core.sms_notifier import send_sms_alert, send_test_sms


def test_send_sms_alert_simulates_when_numbers_unset(monkeypatch):
    import config
    monkeypatch.setattr(config, "TWILIO_FROM_NUMBER", "")
    monkeypatch.setattr(config, "TWILIO_TO_NUMBER", "")
    monkeypatch.setattr(config, "TWILIO_SMS_ENABLED", True)

    # Should safely return False and not throw
    result = send_sms_alert("ALERT: Restricted area intrusion detected.")
    assert result is False


def test_send_sms_alert_skipped_when_disabled(monkeypatch):
    import config
    monkeypatch.setattr(config, "TWILIO_SMS_ENABLED", False)

    result = send_sms_alert("ALERT: Restricted area intrusion detected.")
    assert result is False


def test_send_sms_alert_successful_dispatch(monkeypatch):
    import config
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "ACmockaccount")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "mocktoken")
    monkeypatch.setattr(config, "TWILIO_FROM_NUMBER", "+15550001")
    monkeypatch.setattr(config, "TWILIO_TO_NUMBER", "+15550002")
    monkeypatch.setattr(config, "TWILIO_SMS_ENABLED", True)

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"sid": "SM123456789"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        # synchronous test
        result = send_sms_alert("ALERT: Restricted area intrusion detected.", async_send=False)
        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.twilio.com/2010-04-01/Accounts/ACmockaccount/Messages.json" in args[0]
        assert kwargs["data"]["From"] == "+15550001"
        assert kwargs["data"]["To"] == "+15550002"
        assert "Restricted area intrusion" in kwargs["data"]["Body"]


def test_test_send_sms_helper(monkeypatch):
    import config
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "ACmockaccount")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "mocktoken")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"sid": "SM999"}

    with patch("requests.post", return_value=mock_resp):
        res = send_test_sms(to_number="+15559999", from_number="+15558888", message="Test")
        assert res["success"] is True
        assert res["sid"] == "SM999"
