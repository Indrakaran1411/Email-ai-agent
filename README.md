# Gmail AI Digest Agent

A simple Python agent that reads Gmail messages, filters them by sender and keywords, summarizes the selected emails using a local Ollama AI instance, and sends a digest back to your Gmail account.

## Features

- Fetches emails from your Gmail inbox
- Filters by `watched_senders`, `keywords`, and `skip_subjects`
- Summarizes each email using Ollama (`llama3.2`)
- Builds a plain-text digest with summaries and action items
- Sends the digest to your configured Gmail address

## Prerequisites

- Python 3.10+ installed
- A Gmail API OAuth client credentials file (`credentials.json`)
- A local Ollama server running at `http://localhost:11434`

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Download Gmail OAuth credentials:

   - Open the Google Cloud Console: https://console.cloud.google.com
   - Create or select a project
   - Enable the Gmail API
   - Create OAuth credentials for a Desktop app
   - Download the JSON file
   - Save it as `credentials.json` in this folder

4. Ensure Ollama is running locally:

   - The agent sends summarization requests to `http://localhost:11434/api/generate`
   - It uses model `llama3.2`

## Configuration

Edit `config.json` to set your preferences.

Example:

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

### Config fields

- `my_email`: The Gmail address to send the digest to
- `watched_senders`: Email addresses or domains to include
- `skip_subjects`: Subjects to ignore when building the digest
- `keywords`: Keywords to match inside subject/body
- `summarization_style`: One of `bullet`, `short`, `tldr`, or `full`
- `max_emails`: Maximum number of inbox messages to fetch
- `digest_email`: Optional recipient email for the digest

## Run

Start the agent:

```bash
python agent.py
```

The first run will open a browser for Gmail OAuth consent and create `token.json`.

## How it works

1. `load_config()` reads or creates `config.json`
2. `get_gmail_service()` authenticates with Gmail and stores `token.json`
3. `fetch_emails()` retrieves recent inbox messages
4. `filter_emails()` applies sender/keyword filters
5. `classify_and_summarize()` sends each email body to Ollama
6. `build_digest()` compiles the final summary text
7. `send_digest()` sends the digest message via Gmail

## Notes

- The agent currently uses a local Ollama endpoint, not a cloud LLM API.
- If a summary request fails, the agent includes a fallback message.
- The digest is displayed on screen before sending for confirmation.

## Troubleshooting

- `credentials.json not found`: download it from Google Cloud Console and place it in the project folder
- `token.json not found`: run the script and complete the OAuth flow
- `Failed to summarize email.`: verify Ollama is running locally at `http://localhost:11434`
- `Send digest to ...? (y/N)`: type `y` to send or `n` to cancel

## Project files

- `agent.py` — main application script
- `config.json` — user configuration and filters
- `credentials.json` — Gmail OAuth client secrets
- `token.json` — stored Gmail auth token
- `requirements.txt` — Python dependencies
- `SETUP.md` — setup instructions
- `README.md` — project documentation
