import httpx
import pytest

from elfin_dev_tools.api import ElfinApiError, ElfinClient, JointStateUnavailable

JOINT_STATE = {
    "stale": False,
    "age_sec": 0.031,
    "names": ["elfin_joint1", "elfin_joint2"],
    "positions": [0.0, -0.5235987755982988],
    "positions_deg": [0.0, -30.0],
}


def client_with(handler):
    return ElfinClient(
        "http://test", timeout=1.0, transport=httpx.MockTransport(handler)
    )


def test_joint_state_returns_payload():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json=JOINT_STATE)

    with client_with(handler) as client:
        assert client.joint_state() == JOINT_STATE

    assert seen == ["http://test/api/joint-state"]


def test_joint_state_503_raises():
    payload = {
        "error": "no joint state received yet",
        "topic": "/joint_states",
        "stale": True,
    }

    with client_with(lambda request: httpx.Response(503, json=payload)) as client:
        with pytest.raises(JointStateUnavailable, match="/joint_states"):
            client.joint_state()


def test_joint_state_503_allow_stale():
    payload = {"stale": True, "names": ["elfin_joint1"], "positions_deg": [-30.0]}

    with client_with(lambda request: httpx.Response(503, json=payload)) as client:
        assert client.joint_state(allow_stale=True) == payload


def test_health_returns_payload():
    payload = {"status": "ok", "joint_state_available": True, "stale": False}

    with client_with(lambda request: httpx.Response(200, json=payload)) as client:
        assert client.health() == payload


def test_connection_error_is_wrapped():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with client_with(handler) as client:
        with pytest.raises(ElfinApiError, match="cannot reach"):
            client.health()


def test_non_json_response_is_wrapped():
    with client_with(lambda request: httpx.Response(502, text="bad gateway")) as client:
        with pytest.raises(ElfinApiError, match="non-JSON"):
            client.health()
