import re

def prioritize(summary):
    summary = summary.lower()

    high_keywords = [
        "urgent", "asap", "immediately", "action required", "respond now",
        "payment due", "invoice", "suspicious login", "security alert", "account locked",
        "unauthorized access", "billing problem", "update payment", "breach", "deadline",
        "password reset", "deactivation", "critical issue", "declined"
    ]

    medium_keywords = [
        "reminder", "follow-up", "check-in", "don't miss", "closing soon", "time-sensitive",
        "review", "notification", "expires", "event", "invitation", "meeting", "webinar",
        "newsletter", "schedule", "upcoming", "application", "survey", "feedback", "policy update"
    ]

    low_keywords = [
        "discount", "offer", "deal", "sale", "new product", "announcement", "launch",
        "thank you", "welcome", "update", "promo", "gift", "reward", "bonus", "referral",
        "points", "subscribe", "unsubscribe", "weekly", "monthly"
    ]

    def match_any(keywords):
        return any(re.search(rf"\b{re.escape(kw)}\b", summary) for kw in keywords)

    if match_any(high_keywords):
        return "High"
    elif match_any(medium_keywords):
        return "Medium"
    elif match_any(low_keywords):
        return "Low"
    else:
        return "Low"  # Default to low if no match
