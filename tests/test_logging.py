"""Logs must never contain credentials or personal details, even at debug level."""
import hashlib
import logging

import pytest

from homismart_client import HomismartClient
from homismart_client.utils import REDACTED, redact, redact_message

from test_v030 import FakeWS, _device_list, _patch_connect, _wait_for

USERNAME = "person@example.com"
PASSWORD = "hunter2-correct-horse"
PASSWORD_HASH = hashlib.md5(PASSWORD.encode()).hexdigest()
REAL_NAME = "Jane Example"
SHARER = "sharer@example.com"

SECRETS = (USERNAME, PASSWORD, PASSWORD_HASH, REAL_NAME, SHARER)


@pytest.mark.asyncio
async def test_debug_log_of_a_whole_session_has_no_secrets(caplog):
    caplog.set_level(logging.DEBUG, logger="homismart_client")
    login_reply = (
        '0003{"result": true, "userId": 1, "realName": "%s", "shouldConfirmTerms": 0}' % REAL_NAME
    )
    ws = FakeWS([login_reply])
    client = HomismartClient(USERNAME, PASSWORD)
    with _patch_connect(ws):
        await client.connect(timeout=5)
        ws.push(_device_list({
            "id": "01000000000001", "type": 1, "name": "Hall socket", "power": False,
            "shared": True, "sharedBy": SHARER,
        }))
        await _wait_for(lambda: client.session.get_device_by_id("01000000000001"))
        await client.session.get_device_by_id("01000000000001").turn_on()
    await client.disconnect()

    sent_login = [m for m in ws.sent if m.startswith("0002")]
    assert PASSWORD_HASH in sent_login[0]  # the server still gets the real login

    for secret in SECRETS:
        assert secret not in caplog.text, f"{secret!r} leaked into the log"
    assert REDACTED in caplog.text
    assert "SENT CMD: LOGIN" in caplog.text  # still logged, just without secrets


@pytest.mark.asyncio
async def test_rejected_login_error_has_no_secrets(caplog):
    caplog.set_level(logging.DEBUG, logger="homismart_client")
    ws = FakeWS(['0003{"result": false, "username": "%s"}' % USERNAME])
    client = HomismartClient(USERNAME, PASSWORD)
    with _patch_connect(ws):
        with pytest.raises(Exception) as err:
            await client.connect(timeout=5)
    await client.disconnect()
    for secret in SECRETS:
        assert secret not in caplog.text
        assert secret not in str(err.value)


def test_redact_handles_nesting_case_and_lists():
    data = {
        "Password": "x", "list": [{"sharedBy": "a@b.c"}, 3], "nested": {"realName": "N"},
        "name": "Hall light",
    }
    assert redact(data) == {
        "Password": REDACTED, "list": [{"sharedBy": REDACTED}, 3],
        "nested": {"realName": REDACTED}, "name": "Hall light",
    }
    assert data["Password"] == "x"  # the original is untouched


def test_redact_message_hides_secrets_and_non_json():
    assert redact_message('0002{"username": "u", "password": "p"}') == (
        '0002{"username": "%s", "password": "%s"}' % (REDACTED, REDACTED)
    )
    body = "not json password=p"
    assert redact_message("0002" + body) == f"0002<{len(body)} characters, not JSON>"
    assert redact_message("0072") == "0072"
