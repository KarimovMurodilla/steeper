import hashlib

import pytest

from steeper import SteeperConfig

BOT_ID = "d74d82b4-7c00-408d-b611-2411e0b3c6f8"
BOT_TOKEN = "123456:ABC-DEF"


def _config(base_url: str = "https://api.example.com") -> SteeperConfig:
    return SteeperConfig(base_url=base_url, bot_id=BOT_ID, bot_token=BOT_TOKEN)


def test_token_hash_is_sha256_of_token() -> None:
    expected = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()
    assert _config().token_hash == expected


def test_webhook_url_uses_bot_id_and_strips_trailing_slash() -> None:
    cfg = _config("https://api.example.com/")
    assert cfg.webhook_url == f"https://api.example.com/v1/communications/webhook/{BOT_ID}"


def test_bot_message_url_uses_bot_id_not_secret() -> None:
    cfg = _config()
    assert cfg.bot_message_url == (
        f"https://api.example.com/v1/communications/webhook/{BOT_ID}/bot-message"
    )
    # The secret must never appear in the URL.
    assert cfg.token_hash not in cfg.bot_message_url


def test_secret_matches_is_true_for_token_hash() -> None:
    cfg = _config()
    assert cfg.secret_matches(cfg.token_hash)
    assert not cfg.secret_matches("nope")


@pytest.mark.parametrize("bad_url", ["ftp://host", "file:///etc/passwd", "gopher://x"])
def test_rejects_non_http_scheme(bad_url: str) -> None:
    with pytest.raises(ValueError, match="http or https"):
        SteeperConfig(base_url=bad_url, bot_id=BOT_ID, bot_token=BOT_TOKEN)


def test_rejects_url_without_host() -> None:
    with pytest.raises(ValueError, match="host"):
        SteeperConfig(base_url="https://", bot_id=BOT_ID, bot_token=BOT_TOKEN)


def test_rejects_empty_bot_id_and_token() -> None:
    with pytest.raises(ValueError, match="bot_id"):
        SteeperConfig(base_url="https://h", bot_id="", bot_token=BOT_TOKEN)
    with pytest.raises(ValueError, match="bot_token"):
        SteeperConfig(base_url="https://h", bot_id=BOT_ID, bot_token="")


def test_warns_on_plaintext_http_to_remote_host(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="steeper"):
        SteeperConfig(base_url="http://remote.example.com", bot_id=BOT_ID, bot_token=BOT_TOKEN)
    assert any("plaintext HTTP" in r.message for r in caplog.records)


def test_no_warning_for_localhost_http(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="steeper"):
        SteeperConfig(base_url="http://localhost:8000", bot_id=BOT_ID, bot_token=BOT_TOKEN)
    assert not caplog.records
