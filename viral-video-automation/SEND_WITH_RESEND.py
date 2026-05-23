import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request


RESEND_URL = "https://api.resend.com/emails"
MAX_ATTACHMENT_BYTES = 30 * 1024 * 1024


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2))
    sys.exit(1)


def build_attachment(path):
    size = os.path.getsize(path)
    if size > MAX_ATTACHMENT_BYTES:
        fail(
            f"Attachment is too large for Resend email delivery: {size} bytes. "
            f"Limit for this script is {MAX_ATTACHMENT_BYTES} bytes."
        )

    filename = os.path.basename(path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")

    return {
        "filename": filename,
        "content": encoded,
        "content_type": content_type,
    }


def send_email(api_key, sender, recipient, subject, body, attachment_path):
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": body,
    }
    if attachment_path:
        payload["attachments"] = [build_attachment(attachment_path)]
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "daily-quote-video-automation/1.0",
            **({"Idempotency-Key": os.environ["RESEND_IDEMPOTENCY_KEY"]} if os.environ.get("RESEND_IDEMPOTENCY_KEY") else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"Resend API error {error.code}: {details}")
    except Exception as error:
        fail(f"Resend send failed: {error}")

    print(json.dumps({"ok": True, "resend": result}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="ori.fellous21@gmail.com")
    parser.add_argument("--from-email", default=os.environ.get("RESEND_FROM", "Daily Quote Videos <onboarding@resend.dev>"))
    parser.add_argument("--subject", default="Daily quote video")
    parser.add_argument("--body", required=True)
    parser.add_argument("--attachment")
    args = parser.parse_args()

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        fail("RESEND_API_KEY is not set.")
    if args.attachment and not os.path.exists(args.attachment):
        fail(f"Attachment does not exist: {args.attachment}")

    send_email(api_key, args.from_email, args.to, args.subject, args.body, args.attachment)


if __name__ == "__main__":
    main()
