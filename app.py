from flask import Flask, render_template, request
from email_reader import fetch_emails
from summarizer import summarize_email
from prioritizer import prioritize
from concurrent.futures import ThreadPoolExecutor
import os
from werkzeug.utils import secure_filename
from ocr import extract_text_from_image

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def process_email(e):
    summary = summarize_email(e["body"], html_fallback=e.get("html"))
    priority = prioritize(f"{summary} {e['body']}")
    return {
        "subject": e["subject"],
        "from": e.get("from", "(Unknown)"),
        "summary": summary,
        "priority": priority
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Image summary flow
        if 'image' in request.files and request.files['image'].filename != "":
            image = request.files['image']
            filename = secure_filename(image.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(path)

            text = extract_text_from_image(path)
            summary = summarize_email(text)
            return render_template("inbox.html", emails=[{
                "subject": "Image Summary",
                "from": "Image Upload",
                "summary": summary,
                "priority": prioritize(summary)
            }], sender_filter="")

        # Email login and search flow
        email_address = request.form["email"]
        password = request.form["password"]
        max_emails = int(request.form.get("count", 10))
        unread_only = request.form.get("unread_only") == "on"
        sender_filter = request.form.get("sender_filter", "").lower()

        try:
            raw_emails = fetch_emails(email_address, password, max_emails, unread_only)

            with ThreadPoolExecutor() as executor:
                emails = list(executor.map(process_email, raw_emails))

            if sender_filter:
                emails = [e for e in emails if sender_filter in e["from"].lower()]

            return render_template("inbox.html", emails=emails, sender_filter=sender_filter,
                                   email=email_address, password=password, count=max_emails,
                                   unread_only=unread_only)

        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")
