"""Tests for API retry logic in nova.api.external_services."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestRetryLogic:
    """Retry with exponential backoff for HTTP calls."""

    def test_get_json_retries_on_failure(self):
        from nova.api.external_services import ExternalServices

        svc = ExternalServices({"enabled": True})

        with patch("nova.api.external_services.urllib.request.urlopen") as mock_open:
            import urllib.error
            mock_open.side_effect = urllib.error.URLError("timeout")

            with patch("nova.api.external_services.time.sleep") as mock_sleep:
                result = svc._get_json("http://example.com/test", max_retries=3)

            assert result is None
            assert mock_open.call_count == 3
            # Should have slept twice (between attempt 1→2 and 2→3)
            assert mock_sleep.call_count == 2

    def test_get_json_succeeds_on_second_attempt(self):
        from nova.api.external_services import ExternalServices

        svc = ExternalServices({"enabled": True})

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("nova.api.external_services.urllib.request.urlopen") as mock_open:
            import urllib.error
            mock_open.side_effect = [
                urllib.error.URLError("timeout"),
                mock_response,
            ]

            with patch("nova.api.external_services.time.sleep"):
                result = svc._get_json("http://example.com/test", max_retries=3)

        assert result == {"ok": True}
        assert mock_open.call_count == 2

    def test_post_json_retries_on_failure(self):
        from nova.api.external_services import ExternalServices

        svc = ExternalServices({"enabled": True})

        with patch("nova.api.external_services.urllib.request.urlopen") as mock_open:
            import urllib.error
            mock_open.side_effect = urllib.error.URLError("connection refused")

            with patch("nova.api.external_services.time.sleep") as mock_sleep:
                result = svc._post_json(
                    "http://example.com/api",
                    {"key": "value"},
                    max_retries=2,
                )

            assert result is None
            assert mock_open.call_count == 2
            assert mock_sleep.call_count == 1

    def test_get_json_no_retry_on_success(self):
        from nova.api.external_services import ExternalServices

        svc = ExternalServices({"enabled": True})

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("nova.api.external_services.urllib.request.urlopen") as mock_open:
            mock_open.return_value = mock_response
            result = svc._get_json("http://example.com/test", max_retries=3)

        assert result == {"status": "ok"}
        assert mock_open.call_count == 1

    def test_single_retry_max(self):
        """max_retries=1 means no retries, just one attempt."""
        from nova.api.external_services import ExternalServices

        svc = ExternalServices({"enabled": True})

        with patch("nova.api.external_services.urllib.request.urlopen") as mock_open:
            import urllib.error
            mock_open.side_effect = urllib.error.URLError("timeout")

            with patch("nova.api.external_services.time.sleep") as mock_sleep:
                result = svc._get_json("http://example.com/test", max_retries=1)

            assert result is None
            assert mock_open.call_count == 1
            assert mock_sleep.call_count == 0
