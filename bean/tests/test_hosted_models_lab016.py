"""Lab016 offline tests of hosted LLM transport, safety and scoring."""
import json
from unittest.mock import patch
import urllib.error

import pytest

from bean.evaluation.hosted_models_lab016 import (
    Budget, GitHubModelsAdapter, smoke, run_real, ENDPOINT
)
from bean.evaluation.investigation_lab014 import _prompt


class MockResponse:
    def __init__(self, text):
        self.payload = {
            "choices": [{"message": {"content": text}}]
        }
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, size=100000):
        return json.dumps(self.payload).encode()


def answer():
    return json.dumps({
        "action":"answer","tool":None,"verdict":"nominal",
        "evidence_refs":["verified-smoke"],"confidence":0.9
    })


def test_bounded_budget_enforces_ceiling():
    budget=Budget(2,0)
    assert budget.start()
    assert budget.start()
    assert not budget.start()
    assert budget.used==2
    assert budget.errors["budget_exhausted"]==1


def test_token_not_configured_reports_unavailable():
    adapter=GitHubModelsAdapter(token="",budget=Budget(2,0))
    assert smoke(adapter)=={"status":"unavailable","reason":"no_token"}
    assert adapter.budget.used==0


def test_successful_real_protocol_smoke_without_network():
    adapter=GitHubModelsAdapter(token="synthetic-test-token",budget=Budget(2,0))
    with patch("urllib.request.urlopen",return_value=MockResponse(answer())) as open_mock:
        assert smoke(adapter)["status"]=="passed"
        request=open_mock.call_args.args[0]
    assert request.full_url==ENDPOINT
    body=json.loads(request.data.decode())
    assert body["model"]=="openai/gpt-4.1-mini"
    assert body["messages"][1]["role"]=="user"
    assert "EXAM_INPUT:" in body["messages"][1]["content"]
    assert "synthetic-test-token" not in request.data.decode()
    assert "true_state" not in body["messages"][1]["content"]
    assert adapter.budget.used==1


def test_hosted_model_bad_answer_is_not_passed():
    adapter=GitHubModelsAdapter(token="synthetic",budget=Budget(2,0))
    with patch("urllib.request.urlopen",return_value=MockResponse('{"hello":"world"}')):
        assert smoke(adapter)["status"]=="responded_but_failed_smoke"


def test_403_response_keeps_error_not_claims():
    adapter=GitHubModelsAdapter(token="synthetic",budget=Budget(2,0))
    exc=urllib.error.HTTPError(ENDPOINT,403,"Forbidden",{},None)
    with patch("urllib.request.urlopen",side_effect=exc):
        assert smoke(adapter)=={"status":"unavailable","reason":"http_403"}
    assert adapter.budget.errors=={"http_403":1}


def test_missing_key_never_falls_back_to_emulator():
    result=run_real(token="",max_calls=2,interval=0)
    assert result["status"]=="unavailable"
    assert result["real_llm_invoked"] is False
    assert "hosted" not in result
    assert "comparison" not in result
    assert result["requests_used"]==0
    assert result["model_weights_trained"] is False


def test_malformed_service_data_is_not_accepted():
    adapter=GitHubModelsAdapter(token="synthetic",budget=Budget(2,0))
    class Wrong:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, n):
            return b'{"choices":[]}'
    with patch("urllib.request.urlopen",return_value=Wrong()):
        result=adapter.complete("test")
    assert not result["ok"]
    assert result["error"]=="empty_choices"


@pytest.mark.parametrize("calls,interval",[(0,0),(121,0),(2,-1),(2,31)])
def test_invalid_budget_rejected(calls,interval):
    with pytest.raises(ValueError):
        Budget(calls,interval)
