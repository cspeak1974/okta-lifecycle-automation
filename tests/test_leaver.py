"""Tests for scripts/leaver.py — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

import pytest

import scripts.leaver as leaver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


FAKE_USER = {
    "id": "00u1ab2cd3EF4GH5IJ6",
    "profile": {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "login": "jane.doe@example.com",
    },
}

FAKE_GROUPS = [
    {"id": "00g1eng0000ABC", "profile": {"name": "Engineering"}},
    {"id": "00g1all0000EVR", "profile": {"name": "Everyone"}},
]

# Everyone is filtered out; only Engineering should be acted on
NON_SYSTEM_GROUPS = [FAKE_GROUPS[0]]


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    def test_happy_path_by_id(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_USER)

            user = leaver.get_user("00u1ab2cd3EF4GH5IJ6")

        assert user["id"] == FAKE_USER["id"]
        mock_get.assert_called_once()

    def test_happy_path_by_login(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_USER)

            user = leaver.get_user("jane.doe@example.com")

        assert user["profile"]["login"] == "jane.doe@example.com"

    def test_404_raises(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(404, text="Not found")

            with pytest.raises(RuntimeError, match="Get user .* failed \\[404\\]"):
                leaver.get_user("nobody@example.com")


# ---------------------------------------------------------------------------
# suspend_user
# ---------------------------------------------------------------------------


class TestSuspendUser:
    def test_happy_path(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200)

            leaver.suspend_user("00u1ab2cd3EF4GH5IJ6")

        mock_post.assert_called_once()
        assert "lifecycle/suspend" in mock_post.call_args[0][0]

    def test_already_suspended_is_no_op(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, text="User is already suspended")

            # should not raise
            leaver.suspend_user("00u1ab2cd3EF4GH5IJ6")

    def test_other_400_raises(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, text="Some other error")

            with pytest.raises(RuntimeError, match="Suspend user failed \\[400\\]"):
                leaver.suspend_user("00u1ab2cd3EF4GH5IJ6")


# ---------------------------------------------------------------------------
# revoke_sessions
# ---------------------------------------------------------------------------


class TestRevokeSessions:
    def test_happy_path(self):
        with patch("scripts.leaver.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(204)

            leaver.revoke_sessions("00u1ab2cd3EF4GH5IJ6")

        mock_delete.assert_called_once()
        assert "sessions" in mock_delete.call_args[0][0]

    def test_error_raises(self):
        with patch("scripts.leaver.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(403, text="Forbidden")

            with pytest.raises(RuntimeError, match="Revoke sessions failed \\[403\\]"):
                leaver.revoke_sessions("00u1ab2cd3EF4GH5IJ6")


# ---------------------------------------------------------------------------
# get_user_groups
# ---------------------------------------------------------------------------


class TestGetUserGroups:
    def test_filters_out_everyone_group(self):
        with patch("scripts.leaver.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_GROUPS)

            groups = leaver.get_user_groups("00u1ab2cd3EF4GH5IJ6")

        assert len(groups) == 1
        assert groups[0]["profile"]["name"] == "Engineering"

    def test_error_raises(self):
        with patch("scripts.leaver.requests.get") as mock_get:
            mock_get.return_value = _mock_response(500, text="Server error")

            with pytest.raises(RuntimeError, match="Get user groups failed \\[500\\]"):
                leaver.get_user_groups("00u1ab2cd3EF4GH5IJ6")


# ---------------------------------------------------------------------------
# remove_user_from_groups
# ---------------------------------------------------------------------------


class TestRemoveUserFromGroups:
    def test_deletes_from_each_group(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(204)

            leaver.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", NON_SYSTEM_GROUPS)

        assert mock_delete.call_count == 1

    def test_404_already_removed_is_ok(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(404)

            # should not raise
            leaver.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", NON_SYSTEM_GROUPS)

    def test_500_raises(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(500, text="Server error")

            with pytest.raises(
                RuntimeError, match="Remove from group 'Engineering' failed \\[500\\]"
            ):
                leaver.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", NON_SYSTEM_GROUPS)


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    def test_happy_path(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200)

            leaver.deactivate_user("00u1ab2cd3EF4GH5IJ6")

        mock_post.assert_called_once()
        assert "lifecycle/deactivate" in mock_post.call_args[0][0]

    def test_already_deactivated_is_no_op(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, text="User is already deactivated")

            # should not raise
            leaver.deactivate_user("00u1ab2cd3EF4GH5IJ6")

    def test_other_error_raises(self):
        with patch("scripts.leaver.requests.post") as mock_post:
            mock_post.return_value = _mock_response(500, text="Server error")

            with pytest.raises(RuntimeError, match="Deactivate user failed \\[500\\]"):
                leaver.deactivate_user("00u1ab2cd3EF4GH5IJ6")


# ---------------------------------------------------------------------------
# send_slack_notification
# ---------------------------------------------------------------------------


class TestSendSlackNotification:
    def test_skips_when_no_webhook_url(self):
        with patch.object(leaver, "SLACK_WEBHOOK_URL", ""):
            with patch("scripts.leaver.requests.post") as mock_post:
                leaver.send_slack_notification("jane.doe@example.com")

        mock_post.assert_not_called()

    def test_posts_when_webhook_configured(self):
        with patch.object(leaver, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/fake"):
            with patch("scripts.leaver.requests.post") as mock_post:
                mock_post.return_value = _mock_response(200)

                leaver.send_slack_notification("jane.doe@example.com")

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert "jane.doe@example.com" in payload["text"]

    def test_failed_webhook_does_not_raise(self):
        with patch.object(leaver, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/fake"):
            with patch("scripts.leaver.requests.post") as mock_post:
                mock_post.return_value = _mock_response(500)

                # should not raise — Slack failure is non-fatal
                leaver.send_slack_notification("jane.doe@example.com")


# ---------------------------------------------------------------------------
# offboard_user (orchestrator)
# ---------------------------------------------------------------------------


class TestOffboardUser:
    def test_happy_path_calls_all_steps(self):
        with (
            patch("scripts.leaver.get_user", return_value=FAKE_USER) as mock_get_user,
            patch("scripts.leaver.suspend_user") as mock_suspend,
            patch("scripts.leaver.revoke_sessions") as mock_revoke,
            patch("scripts.leaver.get_user_groups", return_value=NON_SYSTEM_GROUPS) as mock_groups,
            patch("scripts.leaver.remove_user_from_groups") as mock_remove,
            patch("scripts.leaver.deactivate_user") as mock_deactivate,
            patch("scripts.leaver.send_slack_notification") as mock_slack,
        ):
            result = leaver.offboard_user("jane.doe@example.com")

        assert result == FAKE_USER
        mock_get_user.assert_called_once_with("jane.doe@example.com")
        mock_suspend.assert_called_once_with(FAKE_USER["id"])
        mock_revoke.assert_called_once_with(FAKE_USER["id"])
        mock_groups.assert_called_once_with(FAKE_USER["id"])
        mock_remove.assert_called_once_with(FAKE_USER["id"], NON_SYSTEM_GROUPS)
        mock_deactivate.assert_called_once_with(FAKE_USER["id"])
        mock_slack.assert_called_once_with(FAKE_USER["profile"]["login"])

    def test_skips_group_removal_when_no_groups(self):
        with (
            patch("scripts.leaver.get_user", return_value=FAKE_USER),
            patch("scripts.leaver.suspend_user"),
            patch("scripts.leaver.revoke_sessions"),
            patch("scripts.leaver.get_user_groups", return_value=[]),
            patch("scripts.leaver.remove_user_from_groups") as mock_remove,
            patch("scripts.leaver.deactivate_user"),
            patch("scripts.leaver.send_slack_notification"),
        ):
            leaver.offboard_user("jane.doe@example.com")

        mock_remove.assert_not_called()
