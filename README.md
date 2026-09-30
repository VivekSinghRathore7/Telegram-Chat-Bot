# Telegram Chat Bot

Mobile-first Telegram fictional roleplay chatbot with persistent per-user conversations and a configurable OpenAI-compatible model backend.

## Features

- Telegram long polling (no webhook required)
- Persistent SQLite conversation history
- Per-user scenarios
- Character configuration in `character.json`
- 18+ confirmation gate
- OpenAI-compatible LLM endpoint
- Docker-ready deployment
- Secrets kept in environment variables

## Quick setup

1. In Telegram, open `@BotFather`, run `/newbot`, and copy the bot token.
2. Choose an OpenAI-compatible model/inference provider whose terms permit your intended use.
3. Copy `.env.example` to `.env` and fill in the four values.
4. Install and run:

```bash
pip install -r requirements.txt
python bot.py
```

## Environment variables

- `TELEGRAM_BOT_TOKEN`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `MODEL_ID`

Never commit real tokens or API keys.

## Telegram commands

- `/start` — initialize
- `/iam18` — confirm the user is 18+
- `/scenario <description>` — set a scenario
- `/character` — show the current character
- `/reset` — clear conversation history

## Character customization

Edit `character.json`. Keep adult characters explicitly 18+ for adult scenarios.

## Safety boundary

The application is intended only for adults. Sexual content involving minors or unwilling/unable-to-consent persons is not supported.
