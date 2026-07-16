"""Deterministic spam severity scoring utilities.

This module provides a lightweight rule-based severity engine that evaluates
message content independently from ML confidence scores. It is designed to be
fast, deterministic, and safe for production traffic.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional


URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
SHORTENED_URL_PATTERN = re.compile(
    r"(?:bit\.ly|goo\.gl|tinyurl|t\.co|rebrand\.ly|ow\.ly|is\.gd|tiny\.cc|lnkd\.in)",
    re.IGNORECASE,
)
SUSPICIOUS_DOMAIN_PATTERN = re.compile(
    r"(?:secure|login|verify|account|update|support|bank|paypal|amazon|microsoft|apple|netflix|office)[^\s]{0,20}\.(?:com|net|org|info|xyz|top|online|club|bid)",
    re.IGNORECASE,
)


def _normalize_text(message: Optional[Any]) -> str:
    if message is None:
        return ""
    text = str(message).strip()
    return " ".join(text.split())


def _uppercase_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)


def _punctuation_ratio(text: str) -> int:
    return sum(1 for char in text if char in "!?.")


def _count_repeated_tokens(text: str) -> int:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    counts = 0
    for token in set(tokens):
        if tokens.count(token) >= 3:
            counts += 1
    return counts


def calculate_spam_severity(message: Optional[Any], prediction_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate a deterministic severity score for a message.

    The score is based solely on message content and is intentionally independent
    from model confidence. The engine returns a human-readable score, level,
    detected indicators, and a lightweight breakdown for debugging.
    """

    del prediction_data  # The severity engine is intentionally independent of ML confidence.

    text = _normalize_text(message)
    if not text:
        return {
            "score": 0.0,
            "level": "Low",
            "indicators": [],
            "breakdown": {
                "url_risk": 0.0,
                "keyword_risk": 0.0,
                "formatting_risk": 0.0,
                "urgency_risk": 0.0,
                "social_engineering_risk": 0.0,
                "total_score": 0.0,
            },
        }

    normalized = text.lower()
    urls = URL_PATTERN.findall(text)
    has_url = bool(urls)
    has_shortened_url = bool(SHORTENED_URL_PATTERN.search(text))
    has_suspicious_domain = bool(SUSPICIOUS_DOMAIN_PATTERN.search(text))

    indicators: List[str] = []
    breakdown = {
        "url_risk": 0.0,
        "keyword_risk": 0.0,
        "formatting_risk": 0.0,
        "urgency_risk": 0.0,
        "social_engineering_risk": 0.0,
        "total_score": 0.0,
    }

    def add_indicator(name: str, value: float, bucket: str) -> None:
        if value <= 0:
            return
        indicators.append(name)
        breakdown[bucket] = round(breakdown[bucket] + value, 1)

    if has_url:
        url_score = 2.0 if has_shortened_url or has_suspicious_domain else 1.5
        if len(urls) > 1:
            url_score += 0.5
        add_indicator("Suspicious URL", url_score, "url_risk")
        if has_shortened_url:
            add_indicator("Shortened URL", 0.8, "url_risk")
        if has_suspicious_domain:
            add_indicator("Unknown Domain", 1.0, "url_risk")

    # Keyword-based risk indicators
    if any(token in normalized for token in ["password", "pwd", "credentials", "credential"]):
        add_indicator("Password Request", 2.2, "keyword_risk")
    if any(token in normalized for token in ["otp", "one time password", "verification code", "security code"]):
        add_indicator("OTP Request", 1.8, "keyword_risk")
    if any(token in normalized for token in ["verify", "verify your account", "confirm", "validate"]):
        add_indicator("Verification Request", 1.2, "keyword_risk")
    if any(token in normalized for token in ["bank", "wire transfer", "invoice", "payment", "pay now", "send money"]):
        add_indicator("Financial Scam", 2.0, "keyword_risk")
    if any(token in normalized for token in ["crypto", "bitcoin", "wallet", "investment", "profit"]):
        add_indicator("Crypto Scam", 2.0, "keyword_risk")
    if any(token in normalized for token in ["lottery", "winner", "prize", "claim your reward"]):
        add_indicator("Lottery Scam", 2.0, "keyword_risk")
    if any(token in normalized for token in ["suspend", "deactivate", "terminate", "locked"]):
        add_indicator("Account Suspension", 1.6, "keyword_risk")
    if any(token in normalized for token in ["credential", "steal", "stolen", "phishing", "impersonation"]):
        add_indicator("Credential Theft Keywords", 2.0, "keyword_risk")

    # Urgency and fear tactics
    if any(token in normalized for token in ["urgent", "immediately", "act now", "now", "today"]):
        add_indicator("Urgent Language", 1.1, "urgency_risk")
    if any(token in normalized for token in ["warning", "alert", "danger", "risk", "threat"]):
        add_indicator("Fear Tactics", 1.0, "urgency_risk")
    if any(token in normalized for token in ["legal action", "fine", "arrest", "penalty", "sued"]):
        add_indicator("Threat Language", 1.3, "urgency_risk")

    # Social engineering signals
    if any(token in normalized for token in ["click here", "click", "claim", "free", "winner", "limited time"]):
        add_indicator("Social Engineering", 1.3, "social_engineering_risk")

    # Formatting / abuse signals
    upper_ratio = _uppercase_ratio(text)
    if len(text) >= 8 and upper_ratio > 0.25:
        add_indicator("Uppercase Abuse", 0.9, "formatting_risk")
    punctuation_count = _punctuation_ratio(text)
    if punctuation_count >= 3:
        add_indicator("Excessive Punctuation", 0.8, "formatting_risk")
    repeated_tokens = _count_repeated_tokens(text)
    if repeated_tokens > 0:
        add_indicator("Repeated Spam Patterns", 0.7, "formatting_risk")

    # Combined signal boost
    if len(indicators) >= 3:
        add_indicator("Multiple Spam Signals", 1.0, "social_engineering_risk")

    total_score = round(min(10.0, breakdown["url_risk"] + breakdown["keyword_risk"] + breakdown["formatting_risk"] + breakdown["urgency_risk"] + breakdown["social_engineering_risk"]), 1)
    level = "Low"
    if total_score >= 9.0:
        level = "Critical"
    elif total_score >= 6.0:
        level = "High"
    elif total_score >= 3.0:
        level = "Moderate"

    return {
        "score": total_score,
        "level": level,
        "indicators": sorted(set(indicators)),
        "breakdown": {
            **breakdown,
            "total_score": total_score,
        },
    }
