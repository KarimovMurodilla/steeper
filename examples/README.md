# Steeper examples

Runnable, minimal bots for each supported framework. Each reads its config from
environment variables so you can copy a file and run it as-is.

## Setup

1. Run a Steeper backend (self-hosted) and register a bot to get its `bot_id` (UUID).
2. Copy env and fill values:
   ```bash
   cp examples/.env.example examples/.env
   # edit examples/.env, then:
   set -a && . examples/.env && set +a
   ```
3. Install the example's framework and run it:
   ```bash
   pip install "steeper[aiogram]" && python examples/aiogram_bot.py
   pip install "steeper[telebot]" && python examples/telebot_bot.py
   pip install "steeper[ptb]"     && python examples/ptb_bot.py
   ```

Send `/start` to your bot; the message (and the bot's reply) should appear in Steeper.

## System logs

Every example runs with `capture_logs=True`, so the bot's own `logging` output is
shipped to the platform and shown on the **Logs** page of the operator panel.

- `/start` emits an `INFO` record carrying `extra={"chat_id": ...}`.
- `/boom` fails on purpose and logs the traceback at `ERROR`, so you can see how
  an exception is rendered.

Records are batched (by default up to 100 of them, or every 2 seconds), so a
line can take a moment to appear. Capture is off by default in the library —
drop `capture_logs=True` if you only want conversations mirrored.

## Product events

Every example also reports funnel events with `steeper.track(...)`: `/start`
sends `signup`, and `/buy` sends `checkout_started` followed by
`payment_succeeded`. Send both commands, then open the Funnels page in the
panel and build a funnel over those three names to watch the drop-off.

Two things to expect. Events are batched, so an event appears a few seconds
after the command rather than instantly. And a step whose name does not match
what the bot actually sends reports zero users — indistinguishable from real
non-conversion, which is why the funnel builder suggests names the bot has
already used.

Unlike log capture there is no switch to turn on: tracking costs nothing until
the bot makes its first `track()` call.

Note what the handlers depend on. They take an `EventTracker`, never the
`SteeperMiddleware` — the middleware is registered in the composition root and
not mentioned again. aiogram injects the tracker by parameter name, PTB passes
it through `context.bot_data`, and telebot, which has neither DI nor a context
object, falls back to a module-level name. A handler written this way can be
tested by handing it a fake, with no HTTP client and no dispatcher.
