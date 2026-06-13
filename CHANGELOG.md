# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Packaging & release scaffolding: `LICENSE`, GitHub Actions CI (lint, type-check,
  test matrix on Python 3.10–3.13, per-extra import smoke tests) and PyPI publishing
  via Trusted Publishing (OIDC).
- `examples/` with runnable bots for aiogram, telebot and python-telegram-bot.
- Offline test suite (`tests/`) covering config validation and the HTTP client
  contract (mocked with `respx`).
- `CONTRIBUTING.md` and a backend compatibility matrix in the README.

## [0.1.2] - 2026-04

### Added
- Initial public release: `SteeperMiddleware` integrations for aiogram v3,
  pyTelegramBotAPI and python-telegram-bot v20+, backed by `SteeperRepository`
  and `SteeperClient`. Incoming updates are forwarded and outgoing bot messages
  are recorded; backend failures are non-fatal.

[Unreleased]: https://github.com/KarimovMurodilla/steeper/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/KarimovMurodilla/steeper/releases/tag/v0.1.2
