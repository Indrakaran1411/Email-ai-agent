# Gmail AI Agent — Setup Guide

## Overview

This agent reads Gmail messages, filters them by sender/keyword, summarizes the matched emails using a local Ollama AI instance, and sends a digest back to your Gmail account.

## Prerequisites

- Python 3.10+
- `credentials.json` from Google Cloud Console
- A running local Ollama server at `http://localhost:11434`

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Get Gmail API credentials

1. Open https://console.cloud.google.com
2. Create or select a project
3. Enable the Gmail API
4. Go to "APIs & Services" → "Credentials"
5. Create an OAuth client ID for a Desktop app
6. Download the JSON file
7. Save it as `credentials.json` in the project folder

## Configure `config.json`

Edit `config.json` to match your inbox preferences.

Example configuration:

```json
{
  "my_email": "you@gmail.com",
  "watched_senders": [
    "boss@company.com",
    "alerts@github.com",
    "support@bank.com"
  ],
  "skip_subjects": [
    "Your Gmail AI Digest",
    "Your Daily Gmail Digest"
  ],
  "keywords": [
    "urgent",
    "invoice",
    "meeting",
    "security",
    "deadline"
  ],
  "summarization_style": "short",
  "max_emails": 50,
  "digest_email": "you@gmail.com"
}
```

### `config.json` fields

- `my_email`: recipient email address for the digest
- `watched_senders`: list of senders to match
- `skip_subjects`: list of subjects to ignore in the digest
- `keywords`: list of text keywords to match in subject/body
- `summarization_style`: `bullet`, `short`, `tldr`, or `full`
- `max_emails`: number of messages to fetch
- `digest_email`: email address for digest delivery

## Run the agent

```bash
python agent.py
```

The first run will open a browser for Gmail OAuth consent and create `token.json`.

## Notes

- The agent uses Ollama locally, not a cloud LLM API.
- If the summary request fails, it falls back to a simple failure notice.
- The digest is printed for review before sending.

## Troubleshooting

- `credentials.json not found`: ensure the file is in the project root
- `Failed to summarize email.`: verify Ollama is running locally at `http://localhost:11434`
- `Send digest to ...? (y/N)`: enter `y` to send the digest

## Project files

- `agent.py` — main script
- `config.json` — project settings
- `credentials.json` — Gmail OAuth secrets
- `token.json` — saved Gmail auth token
- `requirements.txt` — dependencies
- `SETUP.md` — setup guide
- `README.md` — project documentation
