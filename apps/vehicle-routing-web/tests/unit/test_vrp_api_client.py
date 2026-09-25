import httpx
import pytest

from tests.conftest import PAYLOAD, SOLVE_RESPONSE
from vehicle_routing_web.data.vrp_api_client import SOLVE_PATH, VrpApiClient
from vehicle_routing_web.domain.exceptions import SolveApiError


def _client(handler, sleeps=None, max_attempts=3) -> VrpApiClient:
    return VrpApiClient(
        "http://solver:8000/",
        timeout_seconds=5,
        max_attempts=max_attempts,
        backoff_seconds=0.5,
        transport=httpx.MockTransport(handler),
        sleep=(sleeps.append if sleeps is not None else lambda _s: None),
    )


def test_success_posts_payload_bytes_verbatim_and_returns_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content
        seen["ctype"] = request.headers["content-type"]
        return httpx.Response(200, json=SOLVE_RESPONSE)

    result = _client(handler).solve(PAYLOAD)

    assert seen == {"url": f"http://solver:8000{SOLVE_PATH}", "body": PAYLOAD, "ctype": "application/json"}
    assert result == SOLVE_RESPONSE


def test_422_maps_to_invalid_payload_with_bounded_detail():
    def handler(_request):
        return httpx.Response(422, json={"detail": "x" * 2000, "title": "Invalid"})

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    err = excinfo.value
    assert (err.error_type, err.http_status) == ("invalid_payload", 422)
    assert err.message.startswith("Invalid solver input: ")
    assert len(err.message) <= len("Invalid solver input: ") + 500


def test_422_without_string_detail_uses_generic_message():
    def handler(_request):
        return httpx.Response(422, json={"detail": [{"loc": ["body"], "msg": "field required"}]})

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert excinfo.value.message == "The solver service rejected the payload as invalid."


def test_retries_503_then_succeeds_with_exponential_backoff():
    responses = iter([503, 503, 200])
    sleeps: list[float] = []

    def handler(_request):
        code = next(responses)
        return httpx.Response(code, json=SOLVE_RESPONSE if code == 200 else {})

    assert _client(handler, sleeps).solve(PAYLOAD) == SOLVE_RESPONSE
    assert sleeps == [0.5, 1.0]


def test_gives_up_after_max_attempts_on_503():
    calls = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(503, text="secret internal body")

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert len(calls) == 3
    assert excinfo.value.error_type == "service_error"
    assert excinfo.value.http_status == 503
    assert "secret" not in excinfo.value.message


def test_plain_500_is_not_retried():
    calls = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(500)

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert len(calls) == 1
    assert excinfo.value.error_type == "service_error"


def test_other_4xx_is_not_retried():
    def handler(_request):
        return httpx.Response(404)

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert (excinfo.value.error_type, excinfo.value.http_status) == ("request_rejected", 404)


def test_connect_error_is_retried_then_mapped():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("boom http://user:pw@solver", request=request)

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert len(calls) == 3
    assert excinfo.value.error_type == "connection_error"
    assert "pw" not in excinfo.value.message


def test_read_timeout_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(SolveApiError) as excinfo:
        _client(handler).solve(PAYLOAD)

    assert len(calls) == 1
    assert excinfo.value.error_type == "timeout"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"status": "OPTIMAL"}),
        httpx.Response(200, json=[1, 2]),
    ],
)
def test_invalid_success_body_is_rejected(response):
    with pytest.raises(SolveApiError) as excinfo:
        _client(lambda _request: response).solve(PAYLOAD)

    assert excinfo.value.error_type == "invalid_response"
