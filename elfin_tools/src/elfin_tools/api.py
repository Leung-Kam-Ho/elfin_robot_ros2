"""HTTP client for the Elfin joint-state API.

No ROS libraries are imported here. The client only needs the Flask endpoint
exposed by ``elfin_web_api`` (default ``http://localhost:5001``).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_API_URL = "http://localhost:5001"
DEFAULT_TIMEOUT_SEC = 3.0


class ElfinApiError(RuntimeError):
    """The API could not be reached or returned an unexpected response."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload


class JointStateUnavailable(ElfinApiError):
    """No fresh joint state is available yet.

    The API returns HTTP 503 until the robot has published a message or when
    the newest message is older than its configured staleness threshold.
    ``payload`` still contains the last known data when the API provides it.
    """


class ElfinClient:
    """Small synchronous client for the Elfin HTTP API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("ELFIN_API_URL", DEFAULT_API_URL)
        ).rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ElfinClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _get(self, path: str) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ElfinApiError(
                "timed out after {:g}s waiting for {}".format(self.timeout, url)
            ) from exc
        except httpx.RequestError as exc:
            raise ElfinApiError("cannot reach {}: {}".format(url, exc)) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ElfinApiError(
                "{} returned non-JSON content (HTTP {})".format(
                    url, response.status_code
                )
            ) from exc

        if not isinstance(payload, dict):
            raise ElfinApiError("{} returned unexpected JSON".format(url))
        return response.status_code, payload

    def health(self) -> dict[str, Any]:
        """Return the API health document."""
        status, payload = self._get("/healthz")
        if status != 200:
            raise ElfinApiError(
                "health check failed with HTTP {}".format(status), payload
            )
        return payload

    def joint_state(self, allow_stale: bool = False) -> dict[str, Any]:
        """Return the latest joint-state document.

        Raises ``JointStateUnavailable`` on HTTP 503 unless ``allow_stale`` is
        true, in which case the API's last-known payload is returned as-is.
        """
        status, payload = self._get("/api/joint-state")
        if status == 200:
            return payload
        if status == 503:
            message = str(payload.get("error", "joint state unavailable"))
            if allow_stale:
                return payload
            topic = payload.get("topic")
            if topic:
                message = "{} (topic {})".format(message, topic)
            raise JointStateUnavailable(message, payload)

        raise ElfinApiError(
            "joint-state request failed with HTTP {}: {}".format(status, payload),
            payload,
        )
