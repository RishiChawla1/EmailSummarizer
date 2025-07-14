import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re

# IMAP mappings for popular email domains
IMAP_SERVERS = {
    "gmail.com": "imap.gmail.com",
    "outlook.com": "imap-mail.outlook.com",
    "hotmail.com": "imap-mail.outlook.com",
    "yahoo.com": "imap.mail.yahoo.com",
    "icloud.com": "imap.mail.me.com"
}

def get_imap_server(email_address):
    domain = email_address.split("@")[-1].lower()
    return IMAP_SERVERS.get(domain, f"imap.{domain}")

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", "", text)         # Remove non-ASCII
    text = re.sub(r"\s+", " ", text)                  # Collapse whitespace
    text = re.sub(r"https?://\S+", "", text)          # Remove links
    text = re.sub(r"membership id[#:\s]*\d+", "", text, flags=re.I)
    return text.strip()

def fetch_emails(email_address, password, max_emails=10, unread_only=False):
    imap_server = get_imap_server(email_address)

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select("inbox")

        search_flag = "UNSEEN" if unread_only else "ALL"
        status, messages = mail.search(None, search_flag)
        if status != "OK" or not messages or not messages[0]:
            return []

        email_ids = sorted(messages[0].split(), reverse=True)[:max_emails]
        emails = []

        for eid in email_ids:
            res, msg_data = mail.fetch(eid, "(RFC822)")
            if res != "OK" or not msg_data or not msg_data[0]:
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            # Decode subject
            raw_subject = msg["Subject"]
            if raw_subject is None:
                subject = "(No Subject)"
            else:
                try:
                    part, encoding = decode_header(raw_subject)[0]
                    subject = part.decode(encoding or "utf-8") if isinstance(part, bytes) else part
                except Exception:
                    subject = "(Unreadable Subject)"

            body = ""
            html_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    disp = str(part.get("Content-Disposition"))

                    if "attachment" in disp:
                        continue

                    try:
                        content = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        content = content.decode(charset, errors="ignore")

                        if ctype == "text/plain" and not body:
                            body = content
                        elif ctype == "text/html" and not html_body:
                            html_body = content
                    except Exception:
                        continue
            else:
                try:
                    ctype = msg.get_content_type()
                    content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    if "html" in ctype:
                        html_body = content
                        body = clean_html(content)
                    else:
                        body = content
                except Exception:
                    body = ""

            # Fallback to HTML body if plain text is short
            fallback_body = clean_html(html_body) if html_body else ""
            preferred_text = body if len(body.split()) > 10 else fallback_body

            cleaned_body = clean_text(preferred_text)
            html_body = html_body or ""

            if not cleaned_body:
                cleaned_body = "(No meaningful content extracted.)"
            sender = msg.get("From", "(Unknown Sender)").strip()

            emails.append({
                "subject": subject.strip(),
                "from": sender,
                "body": cleaned_body,
                "html": html_body
            })


        mail.logout()
        return emails

    except imaplib.IMAP4.error:
        raise RuntimeError("Login failed. Check your email and app password.")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch emails: {str(e)}")
