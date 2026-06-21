# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06

### Changed
- **BREAKING (contract):** outgoing bot messages now go to
  `POST /v1/communications/webhook/{bot_id}/bot-message` with the secret
  (`token_hash`) sent in the `x-telegram-bot-api-secret-token` header — was
  `POST /v1/communications/webhook/{token_hash}/bot-message` (secret in the URL
  path). This matches the incoming-webhook scheme and keeps the secret out of
  URLs/logs. **Requires a Steeper backend with the matching change.**

### Added
- Packaging & release scaffolding: `LICENSE`, GitHub Actions CI (lint, type-check,
  test matrix on Python 3.10–3.13, per-extra import smoke tests) and PyPI publishing
  via Trusted Publishing (OIDC).
- `examples/` with runnable bots for aiogram, telebot and python-telegram-bot.
- Offline test suite (`tests/`) covering config validation and the HTTP client
  contract (mocked with `respx`).
- `CONTRIBUTING.md`, a backend compatibility matrix in the README, and an
  ecosystem overview in `docs/OVERVIEW.md`.

## [0.1.2] - 2026-04

### Added
- Initial public release: `SteeperMiddleware` integrations for aiogram v3,
  pyTelegramBotAPI and python-telegram-bot v20+, backed by `SteeperRepository`
  and `SteeperClient`. Incoming updates are forwarded and outgoing bot messages
  are recorded; backend failures are non-fatal.

[Unreleased]: https://github.com/KarimovMurodilla/steeper/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/KarimovMurodilla/steeper/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/KarimovMurodilla/steeper/releases/tag/v0.1.2
