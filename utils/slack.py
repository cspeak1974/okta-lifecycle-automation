"""
Shared Slack notification helpers for okta-lifecycle-automation.

Posts to channel-specific incoming webhook URLs loaded from the environment:
    SLACK_WEBHOOK_EVENTS — #okta-events channel
    SLACK_WEBHOOK_ERRORS — #okta-errors channel

Failures are non-fatal: a warning is printed but no exception is raised.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_WEBHOOK_EVENTS = os.getenv("SLACK_WEBHOOK_EVENTS", "")
_WEBHOOK_ERRORS = os.getenv("SLACK_WEBHOOK_ERRORS", "")


def notify_event(message: str) -> None:
    """Post message to the #okta-events webhook. No-op if webhook is not configured."""
    if not _WEBHOOK_EVENTS:
        return
    response = requests.post(_WEBHOOK_EVENTS, json={"text": message})
    if not response.ok:
        print(f"Slack events notification failed (non-fatal): {response.status_code}")


def notify_error(message: str) -> None:
    """Post message to the #okta-errors webhook. No-op if webhook is not configured."""
    if not _WEBHOOK_ERRORS:
        return
    response = requests.post(_WEBHOOK_ERRORS, json={"text": message})
    if not response.ok:
        print(f"Slack errors notification failed (non-fatal): {response.status_code}")
