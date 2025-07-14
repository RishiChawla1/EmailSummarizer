# test_summary.py
from summarizer import summarize_email

text = """Hey team, just letting you know that the deadline for the product launch has been extended to June 30th. Please update your calendars and reach out if you have questions."""

summary = summarize_email(text)
print("Summary:", summary)
