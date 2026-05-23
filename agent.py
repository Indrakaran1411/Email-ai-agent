"""
Gmail AI Agent
==============
Reads Gmail → filters emails → summarizes with Gemini AI
→ sends digest back to your Gmail.

SETUP
-----

1. Create virtual environment

   python3 -m venv .venv

2. Activate it

   source .venv/bin/activate

3. Install packages

   pip install google-generativeai google-auth google-auth-oauthlib google-api-python-client

4. Put credentials.json in this folder

5. Get Gemini API key:
   https://aistudio.google.com

6. Export Gemini key

   export GEMINI_API_KEY="your_key_here"

7. Run

   python agent.py
"""

import os
import json
import base64

from datetime import datetime


from dotenv import load_dotenv
load_dotenv()


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env()

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

CONFIG_FILE = "config.json"
TOKEN_FILE = "token.json"


STYLE_MAP = {
    "bullet": "bullet points",
    "short": "short paragraph",
    "tldr": "one-line TLDR",
    "full": "detailed summary with action items",
}


# ─────────────────────────────────────────────────────────────
# CONFIG HELPERS
# ─────────────────────────────────────────────────────────────

def load_config():

    if os.path.exists(CONFIG_FILE):

        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    return {
        "my_email": "",
        "watched_senders": [],
        "keywords": [],
        "summarization_style": "short",
        "max_emails": 20,
    }


def save_config(cfg):

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

    print("Config saved.")


# ─────────────────────────────────────────────────────────────
# GMAIL AUTH
# ─────────────────────────────────────────────────────────────

def get_gmail_service():

    creds = None

    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ─────────────────────────────────────────────────────────────
# EMAIL BODY EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_body(payload):

    if payload.get("mimeType") == "text/plain":

        data = payload.get("body", {}).get("data")

        if data:

            return base64.urlsafe_b64decode(
                data
            ).decode(
                "utf-8",
                errors="ignore"
            )

    for part in payload.get("parts", []):

        result = extract_body(part)

        if result:
            return result

    return ""


# ─────────────────────────────────────────────────────────────
# FETCH EMAILS
# ─────────────────────────────────────────────────────────────

def fetch_emails(service, max_results=20):

    print(f"\n[1/5] Fetching up to {max_results} emails from Gmail…")

    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=max_results,
    ).execute()

    messages = result.get("messages", [])

    emails = []

    for msg in messages:

        raw = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in raw["payload"]["headers"]
        }

        body = extract_body(raw["payload"])

        emails.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": body[:2000],
        })

    print(f"Fetched {len(emails)} emails.")

    return emails


# ─────────────────────────────────────────────────────────────
# FILTER EMAILS
# ─────────────────────────────────────────────────────────────

def filter_emails(emails, cfg):

    print("\n[2/5] Filtering emails…")

    watched = [x.lower() for x in cfg["watched_senders"]]
    keywords = [x.lower() for x in cfg["keywords"]]
    skip_subjects = [x.lower() for x in cfg.get("skip_subjects", [])]

    if not watched and not keywords:
        print("No filters set. Keeping all emails.")
        return emails

    matched = []

    for email in emails:

        # Skip digest emails sent by the agent itself
        if any(s in email["subject"].lower() for s in skip_subjects):
            print(f"Skipping digest email: {email['subject']}")
            continue

        sender = email["from"].lower()
        text = (email["subject"] + " " + email["body"]).lower()

        sender_match = any(w in sender for w in watched)
        keyword_match = any(k in text for k in keywords)

        if sender_match or keyword_match:
            matched.append(email)

    print(f"{len(matched)} emails matched.")
    return matched

# ─────────────────────────────────────────────────────────────
# GEMINI SUMMARIZATION
# ─────────────────────────────────────────────────────────────
def classify_and_summarize(emails, cfg):
    """Use Ollama (local AI) to summarize emails."""

    import os
    import json
    import time
    import urllib.request
    import concurrent.futures

    if not emails:
        return []

    print(f"\n[3/5] Summarizing {len(emails)} emails with Ollama AI...")

    style = STYLE_MAP.get(
        cfg.get("summarization_style", "short"),
        STYLE_MAP["short"]
    )

    results = []

    for i, email in enumerate(emails, 1):

        print(f"\nProcessing email {i}/{len(emails)}...")
        print(f"Subject: {email['subject']}")

        prompt = f"""You are an email summarizer. You must respond with ONLY a JSON object, no other text, no markdown, no explanation.

From: {email['from']}
Subject: {email['subject']}
Date: {email['date']}

Body:
{email['body']}

Respond with ONLY this JSON, nothing else:
{{"summary": "one short sentence summary here", "action_items": ["action 1", "action 2"]}}"""

        try:

            print("Sending request to Ollama...")

            def ask_ollama():
                data = json.dumps({
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                }).encode()

                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )

                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read())
                    return result["response"]

            with concurrent.futures.ThreadPoolExecutor() as executor:

                future = executor.submit(ask_ollama)

                try:
                    raw = future.result(timeout=60)

                except concurrent.futures.TimeoutError:
                    raise Exception(
                        "Ollama request timed out after 60 seconds"
                    )

            print("Received response from Ollama.")

            raw = raw.strip()
            raw = raw.replace("```json", "")
            raw = raw.replace("```", "")
            raw = raw.strip()

            # Extract JSON if Ollama adds extra text
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end != 0:
                raw = raw[start:end]

            print("Raw Ollama response:")
            print(raw)

            try:
                parsed = json.loads(raw)

            except Exception:
                parsed = {
                    "summary": raw,
                    "action_items": []
                }

        except Exception as e:

            print(f"\nOllama Error: {e}")

            parsed = {
                "summary": "Failed to summarize email.",
                "action_items": []
            }

        results.append({
            **email,
            **parsed
        })

        print(f"Done email {i}/{len(emails)}")

        time.sleep(1)

    return results

# ─────────────────────────────────────────────────────────────
# BUILD DIGEST
# ─────────────────────────────────────────────────────────────

def build_digest(processed_emails):

    print("\n[4/5] Building digest…")

    today = datetime.now().strftime(
        "%A, %d %B %Y"
    )

    lines = [
        f"Personal Email Digest — {today}",
        "=" * 50,
        "",
    ]

    actions = []

    for email in processed_emails:

        lines.append(f"From: {email['from']}")
        lines.append(f"Subject: {email['subject']}")
        lines.append(f"Summary: {email['summary']}")
        lines.append("")

        actions.extend(
            email.get("action_items", [])
        )

    if actions:

        lines.append("ACTION ITEMS")
        lines.append("-" * 20)

        for a in actions:
            lines.append(f"• {a}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# SEND DIGEST
# ─────────────────────────────────────────────────────────────

def send_digest(service, digest, cfg):

    print("\n[5/5] Sending digest…")

    to_email = cfg["my_email"]

    print("\nDIGEST PREVIEW\n")
    print(digest)

    confirm = input(
        f"\nSend digest to {to_email}? (y/N): "
    ).strip().lower()

    if confirm != "y":

        print("Cancelled.")

        return

    msg = MIMEMultipart()

    msg["To"] = to_email
    msg["From"] = "me"

    msg["Subject"] = (
        "Your Gmail AI Digest"
    )

    msg.attach(
        MIMEText(digest, "plain")
    )

    raw = base64.urlsafe_b64encode(
        msg.as_bytes()
    ).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    print("Digest sent successfully.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def run_agent():

    print("\nGmail AI Agent")
    print("=" * 40)

    cfg = load_config()

    if not cfg["my_email"]:

        cfg["my_email"] = input(
            "Enter your Gmail address: "
        ).strip()

    if not cfg["watched_senders"]:

        print("\nAdd watched senders.")

        while True:

            sender = input(
                "Sender email (Enter to stop): "
            ).strip()

            if not sender:
                break

            cfg["watched_senders"].append(sender)

    save_config(cfg)

    service = get_gmail_service()

    emails = fetch_emails(
        service,
        cfg["max_emails"]
    )

    matched = filter_emails(
        emails,
        cfg
    )

    processed = classify_and_summarize(
        matched,
        cfg
    )

    digest = build_digest(
        processed
    )

    send_digest(
        service,
        digest,
        cfg
    )

    print("\nAgent complete.")


if __name__ == "__main__":
    run_agent()