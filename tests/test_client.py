import httpx
import pytest
import respx

from steeper import SteeperConfig
from steeper._client import SteeperClient

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"
BASE_URL = "https://api.example.com"


def _client() -> SteeperClient:
    cfg = SteeperConfig(base_url=BASE_URL, bot_id=BOT_ID, bot_token=BOT_TOKEN)
    return SteeperClient(cfg)


@respx.mock
async def test_forward_update_posts_full_payload_with_secret_header() -> None:
    client = _client()
    route = respx.post(client._config.webhook_url).mock(return_value=httpx.Response(200))

    update = {"update_id": 1, "message": {"text": "hi"}}
    await client.forward_update(update)

    assert route.called
    request = route.calls.last.request
    assert request.headers["x-telegram-bot-api-secret-token"] == client._config.token_hash
    import json

    assert json.loads(request.content) == update
    await client.close()


@respx.mock
async def test_log_bot_message_posts_expected_fields() -> None:
    client = _client()
    route = respx.post(client._config.bot_message_url).mock(return_value=httpx.Response(200))

    await client.log_bot_message(chat_id=42, text="hello", message_id=7, date=1700000000)

    import json

    request = route.calls.last.request
    # Secret is authenticated via header, not the URL.
    assert request.headers["x-telegram-bot-api-secret-token"] == client._config.token_hash
    assert client._config.token_hash not in str(request.url)
    payload = json.loads(request.content)
    assert payload == {"chat_id": 42, "text": "hello", "message_id": 7, "date": 1700000000}
    await client.close()


@respx.mock
async def test_log_bot_message_defaults_date_when_omitted() -> None:
    client = _client()
    route = respx.post(client._config.bot_message_url).mock(return_value=httpx.Response(200))

    await client.log_bot_message(chat_id=42, text="hi", message_id=7)

    import json

    payload = json.loads(route.calls.last.request.content)
    assert isinstance(payload["date"], int) and payload["date"] > 0
    await client.close()


@respx.mock
async def test_backend_error_is_non_fatal(caplog: pytest.LogCaptureFixture) -> None:
    client = _client()
    respx.post(client._config.webhook_url).mock(return_value=httpx.Response(500))

    with caplog.at_level("WARNING", logger="steeper"):
        # Must not raise — bot keeps working even if Steeper is down.
        await client.forward_update({"update_id": 1})

    assert any("webhook failed" in r.message for r in caplog.records)
    await client.close()


@respx.mock
async def test_token_hash_is_redacted_from_error_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = _client()
    url = client._config.bot_message_url
    respx.post(url).mock(side_effect=httpx.ConnectError("boom", request=httpx.Request("POST", url)))

    with caplog.at_level("WARNING", logger="steeper"):
        await client.log_bot_message(chat_id=1, text="x", message_id=1)

    for record in caplog.records:
        assert client._config.token_hash not in record.getMessage()
    await client.close()
