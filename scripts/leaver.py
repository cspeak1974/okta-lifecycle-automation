"""
leaver.py — suspend, revoke sessions, remove from groups, and deactivate an Okta user.

Usage:
    # by Okta user ID
    python scripts/leaver.py --user-id 00u1ab2cd3EF4GH5IJ6

    # by login (email) — the script will look up the user ID first
    python scripts/leaver.py --login jane.doe@example.com

Environment variables required (.env):
    OKTA_ORG_URL   — e.g. https://your-org.okta.com
    OKTA_API_TOKEN — Okta API token with User and Group write permissions
    SLACK_WEBHOOK_URL — (optional) Slack incoming webhook for offboarding notification
"""

import argparse
import os
import sys

import requests
from okta_client import OKTA_ORG_URL, _headers, _raise_for_status, get_user

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


# ---------------------------------------------------------------------------
# Step 2: Suspend user
# ---------------------------------------------------------------------------


def suspend_user(user_id: str) -> None:
    """Suspend the user. Idempotent — suspending an already-suspended user is a no-op."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/lifecycle/suspend"
    response = requests.post(url, headers=_headers())
    # 400 with E0000001 means the user is already suspended — treat as success
    if response.status_code == 400 and "already suspended" in response.text.lower():
        print(f"User {user_id} already suspended — skipping.")
        return
    _raise_for_status(response, "Suspend user")
    print(f"Suspended user: {user_id}")


# ---------------------------------------------------------------------------
# Step 3: Revoke all sessions
# ---------------------------------------------------------------------------


def revoke_sessions(user_id: str) -> None:
    """Delete all active sessions for the user."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/sessions"
    response = requests.delete(url, headers=_headers())
    _raise_for_status(response, "Revoke sessions")
    print(f"Revoked all sessions for user: {user_id}")


# ---------------------------------------------------------------------------
# Step 4: Remove from all groups
# ---------------------------------------------------------------------------


def get_user_groups(user_id: str) -> list[dict]:
    """Return all groups the user is a member of (excluding the built-in Everyone group)."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/groups"
    response = requests.get(url, headers=_headers())
    _raise_for_status(response, "Get user groups")
    groups = response.json()
    # The built-in "Everyone" group cannot be removed from — skip it
    return [g for g in groups if g["profile"]["name"] != "Everyone"]


def remove_user_from_groups(user_id: str, groups: list[dict]) -> None:
    """Remove the user from each group. Idempotent — 404 means already removed."""
    for group in groups:
        group_id = group["id"]
        group_name = group["profile"]["name"]
        url = f"{OKTA_ORG_URL}/api/v1/groups/{group_id}/users/{user_id}"
        response = requests.delete(url, headers=_headers())
        # 204 = removed, 404 = already not a member — both are fine
        if response.status_code not in (204, 404):
            _raise_for_status(response, f"Remove from group '{group_name}'")
        print(f"Removed from group: {group_name}")


# ---------------------------------------------------------------------------
# Step 5: Deactivate user
# ---------------------------------------------------------------------------


def deactivate_user(user_id: str) -> None:
    """Deactivate the user. Idempotent — deactivating an already-deactivated user is a no-op."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/lifecycle/deactivate?sendEmail=false"
    response = requests.post(url, headers=_headers())
    # 400 with already deactivated message — treat as success
    if response.status_code == 400 and "already deactivated" in response.text.lower():
        print(f"User {user_id} already deactivated — skipping.")
        return
    _raise_for_status(response, "Deactivate user")
    print(f"Deactivated user: {user_id}")


# ---------------------------------------------------------------------------
# Step 6: Send Slack offboarding notification (optional)
# ---------------------------------------------------------------------------


def send_slack_notification(login: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    message = {
        "text": (
            f":wave: Offboarding complete for *{login}*. "
            "Okta account suspended, sessions revoked, groups removed, and deactivated."
        )
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=message)
    if response.ok:
        print("Slack notification sent.")
    else:
        print(f"Slack notification failed (non-fatal): {response.status_code}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def offboard_user(login_or_id: str) -> dict:
    """Full leaver flow. Returns the user object."""
    user = get_user(login_or_id)
    user_id = user["id"]
    login = user["profile"]["login"]

    suspend_user(user_id)
    revoke_sessions(user_id)

    groups = get_user_groups(user_id)
    if groups:
        remove_user_from_groups(user_id, groups)
    else:
        print("No non-system groups to remove.")

    deactivate_user(user_id)
    send_slack_notification(login)

    print(f"\nLeaver complete for {login}.")
    return user


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offboard an Okta user (leaver).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", help="Okta user ID (e.g. 00u1ab2cd3EF4GH5IJ6)")
    group.add_argument("--login", help="Okta login / email address")
    return parser.parse_args()


def _validate_env() -> None:
    missing = [var for var in ("OKTA_ORG_URL", "OKTA_API_TOKEN") if not os.getenv(var)]
    if missing:
        print(
            f"Error: missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    _validate_env()
    args = _parse_args()
    offboard_user(args.user_id or args.login)
