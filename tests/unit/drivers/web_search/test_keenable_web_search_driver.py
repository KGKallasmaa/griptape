import json

import pytest
from pytest_mock import MockerFixture

from griptape.drivers.web_search.keenable import KeenableWebSearchDriver


class TestKeenableWebSearchDriver:
    @pytest.fixture()
    def mock_post(self, mocker: MockerFixture):
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"title": "foo", "url": "https://example.com/a", "snippet": "baz", "description": ""},
                {"title": "no url", "snippet": "dropped"},
            ]
        }
        return mocker.patch("requests.post", return_value=mock_response)

    def test_keyless_search_uses_public_endpoint_with_title(self, mock_post):
        results = KeenableWebSearchDriver().search("test")

        output = [json.loads(result.value) for result in results]
        assert output == [{"url": "https://example.com/a", "title": "foo", "description": "baz"}]

        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.keenable.ai/v1/search/public"
        assert kwargs["headers"]["X-Keenable-Title"] == "griptape"
        assert "X-API-Key" not in kwargs["headers"]
        assert kwargs["json"] == {"query": "test", "max_results": 5, "disable_cards": True}

    def test_keyed_search_uses_keyed_endpoint(self, mock_post):
        KeenableWebSearchDriver(api_key="test-key", app_title="my-app", mode="realtime", results_count=80).search(
            "test", exclude_domains=["pinterest.com"]
        )

        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.keenable.ai/v1/search"
        assert kwargs["headers"]["X-API-Key"] == "test-key"
        assert kwargs["headers"]["X-Keenable-Title"] == "my-app"
        assert kwargs["json"] == {
            "query": "test",
            "max_results": 50,
            "disable_cards": True,
            "exclude_domains": ["pinterest.com"],
            "mode": "realtime",
        }

    def test_params_are_sent(self, mock_post):
        KeenableWebSearchDriver(params={"disable_cards": False, "published_after": "2026-01-01"}).search("test")

        assert mock_post.call_args.kwargs["json"] == {
            "query": "test",
            "max_results": 5,
            "disable_cards": False,
            "published_after": "2026-01-01",
        }

    def test_search_raises_error(self, mocker: MockerFixture):
        mock_response = mocker.Mock()
        mock_response.status_code = 429
        mock_response.reason = "Too Many Requests"
        mocker.patch("requests.post", return_value=mock_response)

        with pytest.raises(
            Exception,
            match="Keenable Search API returned an error with status code 429 and reason 'Too Many Requests'",
        ):
            KeenableWebSearchDriver().search("test")
