# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0](https://github.com/KarimovMurodilla/steeper/compare/v0.2.0...v0.3.0) (2026-08-31)


### Features

* implement system logs view through steeper platform ([034bb9a](https://github.com/KarimovMurodilla/steeper/commit/034bb9a61ca34fada74804a69f129b22dedeef3d))

## [0.2.0](https://github.com/KarimovMurodilla/steeper/compare/v0.1.5...v0.2.0) (2026-08-16)


### Features

* bound the forward queue, make setup idempotent, close the client ([bdad7fc](https://github.com/KarimovMurodilla/steeper/commit/bdad7fc5742afb28a5bc4200c63d946fc2aedb6a))


### Bug Fixes

* **ptb:** stop storing setup state on frozen PTB objects ([531cdfa](https://github.com/KarimovMurodilla/steeper/commit/531cdfa464ce4946904ed901690a0402e202bbbd))


### Documentation

* correct the backend compatibility version ranges ([cb3304d](https://github.com/KarimovMurodilla/steeper/commit/cb3304ded8684908854ba1fc46b4ab73a031221a))

## [0.1.5](https://github.com/KarimovMurodilla/steeper/compare/v0.1.4...v0.1.5) (2026-08-15)


### Documentation

* correct info, remove duplicates and more ([5b0fa96](https://github.com/KarimovMurodilla/steeper/commit/5b0fa96ebcda5e10f32f09e3b17fe0bc2db2163e))

## [0.1.4](https://github.com/KarimovMurodilla/steeper/compare/v0.1.3...v0.1.4) (2026-07-19)


### Bug Fixes

* move auth secret out of bot-message URL and unblock telebot forwarding ([3e4febf](https://github.com/KarimovMurodilla/steeper/commit/3e4febf1f65b2efc119ce5f817766a38ca66d77b))
* token repr leak and blocking Steeper forwarding in async integrations ([e249ba5](https://github.com/KarimovMurodilla/steeper/commit/e249ba51c4d00c14dc6cbd139f88f2a3de0549a6))

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
