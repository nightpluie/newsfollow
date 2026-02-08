# newsfollow prototype

A practical prototype for your ETtoday workflow:

1. Monitor UDN + TVBS web pages (homepage / marquee / hot)
2. Score and cluster potential major events
3. Generate draft title/body/image prompt (LLM or fallback)
4. Hand off to publisher adapter (stub by default)

## Current Scope

- Included now:
  - Web crawling via `requests + BeautifulSoup`
  - Event clustering + weighted scoring
  - LLM draft generation (OpenAI-compatible API)
  - Publisher adapter (`stub` or shell `command`)
- Intentionally left blank / stub:
  - OpenClaw crawler backend
  - Mobile push notification monitor
  - Direct ETtoday system publishing integration

## Quick Start

```bash
cd /Users/nightpluie/Desktop/newsfollow
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
python3 main.py run-once
```

## Commands

```bash
# run one cycle
python3 main.py run-once

# run one cycle and call publisher adapter
python3 main.py run-once --publish

# loop mode (interval from config)
python3 main.py loop

# list latest events
python3 main.py list-events --limit 30
```

## LLM Setup

Set environment variables before running:

```bash
export OPENAI_API_KEY='your_key'
# optional
export OPENAI_MODEL='gpt-4o-mini'
export OPENAI_BASE_URL='https://api.openai.com/v1/chat/completions'
```

If key is missing, the app still works and outputs fallback drafts.

## Publisher Adapter

In `config.yaml`:

- `publisher.mode: stub`
  - No real publish, only logs.
- `publisher.mode: command`
  - Executes `publish_command` and sends draft JSON via stdin.
  - Command may return JSON: `{"status":"ok","external_id":"...","message":"..."}`

This lets you bridge to your existing ETtoday automation script.

## OpenClaw Note

`crawler_backend: openclaw` is intentionally reserved for future implementation.
The app currently warns and falls back to `requests` backend.

## Suggested Next Step

- Integrate your ETtoday publisher as command adapter first.
- Then add OpenClaw crawler backend and Android push monitor as separate modules.
