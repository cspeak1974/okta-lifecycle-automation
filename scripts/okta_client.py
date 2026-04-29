"""
Shared Okta API helpers used by joiner.py, mover.py, and leaver.py.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

OKTA_ORG_URL = os.getenv("OKTA_ORG_URL", "").rstrip("/")
OKTA_API_TOKEN = os.getenv("OKTA_API_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": f"SSWS {OKTA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _raise_for_status(response: requests.Response, context: str) -> None:
    if not response.ok:
        raise RuntimeError(
            f"{context} failed [{response.status_code}]: {response.text}"
        )


def get_user(login_or_id: str) -> dict:
    """Fetch an Okta user by ID or login (email). Returns the user object."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{login_or_id}"
    response = requests.get(url, headers=_headers())
    _raise_for_status(response, f"Get user '{login_or_id}'")
    user = response.json()
    print(f"Found user: {user['id']} ({user['profile']['login']})")
    return user


def find_groups_for_department(department: str) -> list[dict]:
    """Return all Okta groups whose name contains the department string."""
    url = f"{OKTA_ORG_URL}/api/v1/groups"
    params = {"q": department, "limit": 200}
    response = requests.get(url, headers=_headers(), params=params)
    _raise_for_status(response, "List groups")
    groups = response.json()
    matched = [g for g in groups if department.lower() in g["profile"]["name"].lower()]
    print(
        f"Found {len(matched)} group(s) for department '{department}': "
        f"{[g['profile']['name'] for g in matched]}"
    )
    return matched
