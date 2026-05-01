"""Tests for utils/slack.py — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

import utils.slack as slack

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    return resp


# ---------------------------------------------------------------------------
# notify_event
# ---------------------------------------------------------------------------


class TestNotifyEvent:
    def test_skips_when_no_webhook_url(self):
        with patch.object(slack, "_WEBHOOK_EVENTS", ""):
            with patch("utils.slack.requests.post") as mock_post:
                slack.notify_event("User provisioned: jane.doe@example.com")

        mock_post.assert_not_called()

    def test_posts_to_events_webhook_when_configured(self):
        with patch.object(slack, "_WEBHOOK_EVENTS", "https://hooks.slack.com/fake-events"):
            with patch("utils.slack.requests.post") as mock_post:
                mock_post.return_value = _mock_response(200)

                slack.notify_event("User provisioned: jane.doe@example.com")

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        payload = mock_post.call_args[1]["json"]
        assert url == "https://hooks.slack.com/fake-events"
        assert "jane.doe@example.com" in payload["text"]

    def test_non_200_response_does_not_raise(self):
        with patch.object(slack, "_WEBHOOK_EVENTS", "https://hooks.slack.com/fake-events"):
            with patch("utils.slack.requests.post") as mock_post:
                mock_post.return_value = _mock_response(500)

                # should not raise — Slack failure is non-fatal
                slack.notify_event("User provisioned: jane.doe@example.com")


# ---------------------------------------------------------------------------
# notify_error
# ---------------------------------------------------------------------------


class TestNotifyError:
    def test_skips_when_no_webhook_url(self):
        with patch.object(slack, "_WEBHOOK_ERRORS", ""):
            with patch("utils.slack.requests.post") as mock_post:
                slack.notify_error("Joiner failed for jane.doe@example.com")

        mock_post.assert_not_called()

    def test_posts_to_errors_webhook_when_configured(self):
        with patch.object(slack, "_WEBHOOK_ERRORS", "https://hooks.slack.com/fake-errors"):
            with patch("utils.slack.requests.post") as mock_post:
                mock_post.return_value = _mock_response(200)

                slack.notify_error("Joiner failed for jane.doe@example.com")

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        payload = mock_post.call_args[1]["json"]
        assert url == "https://hooks.slack.com/fake-errors"
        assert "jane.doe@example.com" in payload["text"]

    def test_non_200_response_does_not_raise(self):
        with patch.object(slack, "_WEBHOOK_ERRORS", "https://hooks.slack.com/fake-errors"):
            with patch("utils.slack.requests.post") as mock_post:
                mock_post.return_value = _mock_response(500)

                # should not raise — Slack failure is non-fatal
                slack.notify_error("Joiner failed for jane.doe@example.com")
